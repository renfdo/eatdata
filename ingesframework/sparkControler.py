#felipe
import json
from os import truncate
import boto3
from copy import Error
from botocore.config import Config
from pyspark.sql.functions import lit, col
from awsglue.context import GlueContext
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from ingesframework.ingestConfig import IngestConfig
from ingesframework.ingestReaders import IIngestReaders, ReaderTextFile, ReaderParquet, ReaderJDBC
from ingesframework.ingestTransform import AIngestTransform, RenameCast, CastDate
import importlib
import logging


MSG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(format=MSG_FORMAT, datefmt=DATETIME_FORMAT)
_logger = logging.getLogger('py4j')
_logger.setLevel(logging.INFO)


class SparkController(object):
    
    def __init__(self, configPath, jobName, dtImport, storage_layers) -> None:
        super().__init__()
        self.__job = self.get_job(configPath, jobName)
        self.__dtImport = dtImport
        self.__layers = storage_layers
        
        self.__start_session()
        
        _logger.info("### Iniciando Leitura dos Dados ###")
    
    def ingest_raw(self, isIncremental=True):
        type = self.__job['source']['type']
        source_layer = "landing"
        _logger.info("### Iniciando Leitura da Camada RAW ###")
        _logger.info(self.__job['source'])
        
        if type == "csv" or type == 'txt':
            reader = ReaderTextFile(self.__spark, self.__job['source'], self.__layers)
        elif type == "parquet":
            reader = ReaderParquet(self.__spark, self.__job['source'], self.__layers)
        elif type == "jdbc":
            reader = ReaderJDBC(self.__spark, self.__job['source'], self.__layers)
        else:
            raise Error("Unable to read this format")
        
        self.__df = self.__read_source(reader, source_layer)
        
        # carga full ou incremental
        if isIncremental and "conditions" in self.__job['source']:
            _logger.info("Validando incremento")
            self.__df = reader._filter_conditions(self.__df, self.__dtImport, 'yyyyMMdd')
        
        self.save_raw()
    
    def ingest_trusted(self):
        # ingest always get data from raw zone
        source_layer = "raw"
                                             
        reader = ReaderParquet(self.__spark, self.__job['destination'], self.__layers)
        _logger.info("### Iniciando Leitura do parquet ###")
        _logger.info(self.__job['destination'])
        
        
        self.__df = self.__read_source(reader, source_layer)
        

        if self.__df:
            # filter by dtimport from raw
            self.__df = self.__df.filter(col('DT_IMPORT') == self.__dtImport)
            _logger.info("Data a ser importada/filtrada 'dt_import' {}".format(self.__dtImport))
            
            _logger.info("Total de registros a serem importados {}".format(self.__df.count()))
        
            #self.__df = self.__df.limit(100)
            #self.__df.printSchema()
        
            if self.__df.limit(1).count() > 0:
                if "transformations" in self.__job['destination']['trusted']:
                    self.exec_transformations(self.__job['destination']['trusted']['transformations'])
        
                self.save_trusted()

    def exec_transformations(self, transformations):
        _logger.info("Realizando transformações") 
        df = self.__df
        _logger.info("#########################")
        _logger.info("Executando transformações")
        
        for transformation in transformations:
            _logger.info("Importando Lib "+transformation['name'])
            
            module = importlib.import_module("ingesframework.ingestTransform")
            transform = getattr(module, transformation['name'])
            
            df = transform(self.__spark,self.__df, transformation['parameters']).transform()

                                                            
        self.__df = df
        
    def save_trusted(self):
        # path variable get bucket and directory from raw 
        # path is always equal, for raw and trusted. Just the bucket is difference
        layer_destination = 'trusted'
        path = self.__get_path(layer_destination,self.__job['destination']['path'])
        ingest_type = self.__job['destination'][layer_destination]['ingest_type']
        
        _logger.info("Salvando Parâmetros... Destination: "+layer_destination+".... Path: "+path+"... ingest_type: "+ingest_type )
        
        #self.__df.show(truncate=False)
        
        df = self.__df.write
        
        if ingest_type in ["Replace", "ReplacePartition"]:
            table_format = 'parquet'
            table_mode = 'overwrite'
        
            mode = "static" if ingest_type == "Replace" else "dynamic"
            self.__spark.conf.set("spark.sql.sources.partitionOverwriteMode",mode)
            
            _logger.info("Definindo Parâmetros de Ingestão... Ingest_type: "+ingest_type+".... table_format: "+table_format+"... table_mode: "+table_mode+"... mode: "+mode)
            
            df = df.format(table_format)\
                    .mode(table_mode)
             

            if "options" in self.__job['destination'][layer_destination]:
                df = df.options(**self.__job['options'])
                            
            if "partitions" in self.__job['destination'][layer_destination]:
                df = df.partitionBy(*self.__job['destination'][layer_destination]['partitions'])
                
            df = df.option('path',path)
            
            if 'database' in self.__job['destination'][layer_destination]:
                database = self.__job['destination'][layer_destination]['database']
                table = self.__job['destination']['table_name']
                
                df.saveAsTable("{}.{}".format(database,table))
                _logger.info("Definindo Parâmetros de Ingestão... Database: "+database+".... Table: "+table)
        
            else:
                df.save()
                _logger.info("Arquivo parquet salvo no destino "+path)
                
        elif ingest_type == "Upsert":
            table = self.__job['destination']['table_name']
            if 'database' in self.__job['destination'][layer_destination]:
                database = self.__job['destination'][layer_destination]['database']
            table_format = 'hudi'
            
            _logger.info("Definindo Parâmetros de Ingestão... Ingest type: "+ingest_type+" .... Table Format: "+table_format+" ... Table: "+table+" ... Database: "+database)
           
            
            record_key_list=",".join(self.__job['destination'][layer_destination]['key_column'])


            spark_options = {
              'hoodie.table.name': table,
              'hoodie.datasource.write.table.name': table,
              'hoodie.consistency.check.enabled': True,
              'hoodie.datasource.write.recordkey.field': record_key_list,
              'hoodie.datasource.write.operation': 'upsert',
              'hoodie.datasource.write.precombine.field': self.__job['destination'][layer_destination]['order_column'],
              'hoodie.datasource.hive_sync.use_jdbc': False
            }
            
            if "partitions" in self.__job['destination'][layer_destination]:
                partition_list=",".join(self.__job['destination'][layer_destination]['partitions'])
                spark_options['hoodie.datasource.hive_sync.partition_fields'] = partition_list
            
            if len(self.__job['destination'][layer_destination]['key_column']) > 0:
                spark_options['hoodie.datasource.write.keygenerator.class'] = 'org.apache.hudi.keygen.ComplexKeyGenerator'
        
            else:
                spark_options['hoodie.datasource.write.keygenerator.class'] = 'org.apache.hudi.keygen.NonpartitionedKeyGenerator'
                
            if 'database' in self.__job['destination'][layer_destination]:
                if "partitions" in self.__job['destination'][layer_destination]:
                    spark_options['hoodie.datasource.hive_sync.partition_extractor_class'] = 'org.apache.hudi.hive.MultiPartKeysValueExtractor'
                else:
                    spark_options['hoodie.datasource.hive_sync.partition_extractor_class'] = 'org.apache.hudi.hive.NonPartitionedExtractor'
                    spark_options['hoodie.datasource.write.keygenerator.class'] = 'org.apache.hudi.keygen.NonpartitionedKeyGenerator'
                
                spark_options = {**spark_options, 
                  'hoodie.datasource.hive_sync.enable': 'true',
                  'hoodie.datasource.hive_sync.table': table,
                  'hoodie.datasource.hive_sync.database': database
                }
            else:
                spark_options['hoodie.datasource.hive_sync.enable'] = 'false'
            
            table_mode = 'append'
            _logger.info("Definindo Parâmetros de Ingestão... table_mode: "+table_mode)

            df = df.format(table_format)\
                .options(**spark_options)\
                .mode(table_mode)

            if "partitions" in self.__job['destination'][layer_destination]:
                df.partitionBy(*self.__job['destination'][layer_destination]['partitions'])
                
            df.save(path)
            _logger.info("Os dados foram carregados com sucesso!")
        else:
            raise Error("Ingest type was not recognize")
            
        
    def get_job(self, configPath, jobName):
        jobs = IngestConfig(configPath).get_config()
        for job in jobs:
            if job['job_name'] == jobName:
                return job
        raise Error(f'Job não localizado no arquivo de parametro: {jobName}')
        
    def __start_session(self):
        # ativa o spark session        
        self.__spark = SparkSession.builder.config('spark.serializer','org.apache.spark.serializer.KryoSerializer') \
                        .config("spark.sql.legacy.parquet.datetimeRebaseModeInRead", "LEGACY") \
                        .config('spark.sql.hive.convertMetastoreParquet','false').getOrCreate()
        sc = self.__spark.sparkContext
              
    def __read_source(self, reader: IIngestReaders, layer):
        return reader.get_df(layer)

    def __get_path(self, layer,path):
        bucket = self.__layers[layer]['path']

        if bucket[-1] != "/":
            bucket=bucket+'/'
        return bucket+path

    def columns_uppercase(self, df):
        return df.toDF(*[column.upper() for column in df.columns])    
      
    def save_raw(self):
        self.__spark.conf.set("spark.sql.sources.partitionOverwriteMode","dynamic")
                       
        # path obtem o bucket/pasta que representa a camada RAW
        path = self.__get_path('raw',self.__job['destination']['path'])

        # sempre gera uma nova coluna DT_IMPORT
        df = self.__df.withColumn('DT_IMPORT',lit(self.__dtImport))
        df = self.columns_uppercase(df)
        #df = df.limit(100)

        #df.show(truncate=False)
        
        if 'database' in self.__job['destination']['raw']:
            database = self.__job['destination']['raw']['database']
            table = self.__job['destination']['table_name']
            
            df.write \
            .format('parquet') \
            .option('path',path) \
            .mode("overwrite") \
            .partitionBy("DT_IMPORT") \
            .saveAsTable("{}.{}".format(database,table))
        else:
            df.write \
            .format('parquet') \
            .option('path',path) \
            .mode("overwrite") \
            .partitionBy("DT_IMPORT") \
            .save()
        
        _logger.info("Os dados foram carregados com sucesso!")