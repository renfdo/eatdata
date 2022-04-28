import json
import boto3
from botocore.config import Config
#Responsável de fazer a leitura do arquivo json de configução que contem as origens e destinos dos dados.
class IngestConfig(object):
    
    def __init__(self, path) -> None:
        super().__init__()
        self.__path = path
        
        self.read_config()
        
    def read_s3(self):
        s3 = boto3.resource('s3')
        path = self.__path.replace('s3://','').split('/')
        bucket = path[0]
        path = "/".join(path[1:])
        
        content_object = s3.Object(bucket, path)
        file_content = content_object.get()['Body'].read().decode('utf-8')
        
        return file_content
    
    def read_local(self):
        return open(self.__path)

    def read_config(self):
        try:
            if self.__path[:5] == 's3://':
                config = json.loads(self.read_s3())
            else:
                config = json.load(self.read_local())
        
            self.__config = config
        except Exception as e:
            raise Exception("Erro na ao ler arquivo de parametros")
    
    def get_config(self):
        return self.__config    
