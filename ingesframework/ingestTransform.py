
from os import truncate
import boto3
import logging
from copy import Error
from pyspark.sql import DataFrame
from abc import abstractclassmethod
from pyspark.sql.functions import unix_timestamp, from_unixtime, col, trim

MSG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(format=MSG_FORMAT, datefmt=DATETIME_FORMAT)
_logger = logging.getLogger('py4j')
_logger.setLevel(logging.INFO)

class AIngestTransform:
    def __init__(self, spark, df, parameters) -> None:
        self._df = df
        self._parameters = parameters
   
    @abstractclassmethod
    def transform(self) -> DataFrame:
        raise NotImplementedError
    
class RenameCast(AIngestTransform):
    
    def __init__(self, spark, df, parameters) -> None:
        super().__init__(spark, df, parameters)
        
    def transform(self) -> DataFrame:
        df = self._df
        #validate(instance=parameters, schema=schema_parameters)
        for column in self._parameters:
            df = df.withColumn(column['column_name'],df[column['column_name']].cast(column['data_type']))\
                .withColumnRenamed(column['column_name'], column['new_column_name'])
        return df

class CastDate(AIngestTransform):
    
    def __init__(self, spark, df, parameters) -> None:
        super().__init__(spark, df, parameters)
        
    def transform(self) -> DataFrame:
        df = self._df

        for column in self._parameters:
            df = df.withColumn(column['column_name'],
                            from_unixtime(unix_timestamp(col(column['column_name']), column['source_format'])).cast("Date")
                )
        return df

class Trim(AIngestTransform):
    
    def __init__(self, spark, df, parameters) -> None:
        super().__init__(spark, df, parameters)
        
    def transform(self) -> DataFrame:
        df = self._df
        
        for column in self._parameters:
            
            if column['column_name'] == "*":
                df = self.all_columns(df)
            else:
                df = df.withColumn(column['column_name'],trim(col(column['column_name'])))
        return df
        
    def all_columns(self, df):
        all = df.columns
        for column in all:
            # a coluna DT_IMPORT foi criada na etapa RAW, portanto ja é certeza que não precisamos fazer o trim
            if column != 'DT_IMPORT':
                df = df.withColumn(column,trim(col(column)))
        return df