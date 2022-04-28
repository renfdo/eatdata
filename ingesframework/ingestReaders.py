import json
from os import truncate
import boto3
from copy import Error
from pyspark.sql import DataFrame
from abc import abstractclassmethod
from pyspark.sql.functions import unix_timestamp, from_unixtime, col, lit
from pyspark.sql.utils import AnalysisException
import logging

MSG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(format=MSG_FORMAT, datefmt=DATETIME_FORMAT)
_logger = logging.getLogger('py4j')
_logger.setLevel(logging.INFO)

class IIngestReaders:
    def __init__(self, spark, source, storage_config) -> None:
        self._source = source
        self._spark = spark
        self._storage_config = storage_config
        
        _logger.info(storage_config["raw"]["path"])
        _logger.info(storage_config["trusted"]["path"])

    @abstractclassmethod
    def get_df(self, layer: None) -> DataFrame:
        raise NotImplementedError
    
    def _get_path(self, layer,path):
        bucket = self._storage_config[layer]['path']
        
        if bucket[-1] != "/":
            bucket=bucket+'/'
        return bucket+path
    
    def _get_secret(self, secret_name):
        _logger.info(f"Getting secret manager: {secret_name}")
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager')
        secret = client.get_secret_value(SecretId=secret_name)
        
        return json.loads(secret['SecretString'])
    
    def _filter_conditions(self, df, compare_to, format):
        # não implementado
        # necessario criar um padrão no objeto conditions que atenda criterios de carga incremental
        # como por exemplo coluna_data = data atual - 7      
        sql = f"SELECT * FROM table_filter WHERE "
        remove_columns = ['dt_corte']
        
        # column to filtered with source columns
        df = df.withColumn(f'dt_corte',from_unixtime(unix_timestamp(lit(compare_to), format)))
        
        for index, condition in enumerate(self._source['conditions']):
            date_format= condition['date_format'] if "date_format" in condition else None
            column = condition['filter_date']
            days = condition['days']
            compare=condition['compare']
            
            filter_column = f'{column}_ingestFrameWork'
            if filter_column not in remove_columns:
                remove_columns.append(filter_column)

            if date_format:
                df = df.withColumn(f'{filter_column}',from_unixtime(unix_timestamp(col(column), date_format)))
            else:
                df = df.withColumn(f'{filter_column}',col(column))

            if index != 0:
                sql = sql+"and " 
            sql = sql+f"{filter_column} {compare} date_add(dt_corte,{days})"            
       
        _logger.info("########################")
        _logger.info("########################")
        _logger.info("########################")
        _logger.info(f"Filter: {sql}")
        _logger.info("########################")
        _logger.info("########################")
        _logger.info("########################")

        df.registerTempTable("table_filter")
        df = self._spark.sql(sql)
        df = df.drop(*remove_columns)
        
        return df
              
class ReaderTextFile(IIngestReaders):

    def __init__(self, spark, source, storage_config) -> None:
        super().__init__(spark, source, storage_config)
        
    def __set_columns(self, df, columns):
        if len(columns) != len(df.columns):
            raise Error('Atributte "columns" must have the same size that Source dataframe')
        return df.toDF(*columns)
       
    def get_df(self, layer) -> DataFrame:
        path = self._get_path(layer, self._source['path'])
        
        df = self._spark \
                    .read \
                    .format(self._source['type'])
        
        if "options" in self._source:
            df = df.options(**self._source['options'])

        df = df.csv(path)
        
        if "columns" in self._source:
            df = self.__set_columns(df,self._source['columns'])            
        return  df 

class ReaderParquet(IIngestReaders):

    def __init__(self, spark, source, storage_config) -> None:
        super().__init__(spark, source, storage_config)

    def get_df(self,layer):
        path = self._get_path(layer, self._source['path'])
        
        df = self._spark \
                    .read \
                    .format("parquet")
        
        if "options" in self._source:
            df = df.options(**self._source['options'])
        
        try:
            return df.load(path)
        except AnalysisException:
            _logger.info("Data Frame empty")
            return None

class ReaderJDBC(IIngestReaders):
    
    driver_options = {
        "sqlserver": {
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
        },
        
        "oracle": {
            "driver": None
        }
    }

    def __init__(self, spark, source, storage_config) -> None:
        super().__init__(spark, source, storage_config)
        _logger.info("Starting read data from Source")
        
    def get_url(self, source, secretvalue):        
        if source['dbtype'] == "sqlserver":
            return "jdbc:sqlserver://{}:{};databaseName={}".format(
                secretvalue['host'],
                secretvalue['port'],
                secretvalue['dbname']
            )
        raise Error("dbtype is not implemented on ingetFramework yet")

    def get_df(self, source_layer) -> DataFrame:        
        source = self._source
        secret = self._get_secret(self._source['secret_name'])
        
        url = self.get_url(source, secret)
        driver = self.driver_options[source['dbtype']]['driver']

        df = self._spark.read.format("jdbc") \
            .option("url", url) \
            .option("user", secret['username']) \
            .option("password", secret['password']) \
            .option("driver", driver)
            
        if "query" in source:
            df = df.option("query", source['query'])
        else:
            df = df.option("dbtable", source['table'])

        if "options" in source:
            df = df.options(**source['options'])
    
        return df.load()
    