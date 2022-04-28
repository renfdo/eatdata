import sys
import logging
import argparse
from ingesframework.sparkControler import SparkController
from ingesframework.config import get_layers
from awsglue.utils import getResolvedOptions
from datetime import datetime
from awsglue.context import GlueContext
from pyspark.context import SparkContext

MSG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(format=MSG_FORMAT, datefmt=DATETIME_FORMAT)
logger = logging.getLogger('py4j')
logger.setLevel(logging.INFO)

def get_date_parameters():
    dtimport = datetime.now()
    dtimport = dtimport.strftime('%Y%m%d')
    
    return dtimport

if __name__ == '__main__':
    logger.info("Iniciando IngestFramework")
    
    # parametros obrigatórios
    params = [
    'parametros',
    'job',
    'isIncremental',
    'step',
    'account',
    'env',
    'domain'
    ]
    
    args = getResolvedOptions(sys.argv, params)
    
    logger.info("Parametros "+",".join(sys.argv))
    

    if '--dtimport' in sys.argv:
        dt_parameter = sys.argv[sys.argv.index('--dtimport')+1]
        # converte para data para validação e converte para string novamente
        dtimport = datetime.strptime(dt_parameter,'%Y%m%d').strftime('%Y%m%d')
        
        logger.info("dtImport informando no parametro da execução "+dtimport)
    else:
        dtimport = get_date_parameters()
        logger.info("dtImport definida por padrão "+dtimport)
        
    storage_layers = get_layers(args['account'], args['env'], args['domain'])
    
    # concatena bucket artifact com caminho do json de parametros
    parametros = storage_layers['artifact']['path']+args['parametros']
    
    controller = SparkController(parametros, args['job'],dtimport, storage_layers)

    if args['step'] == 'raw':
        logger.info("Iniciando carga da origem para camada RAW")
        isIncremental = False if args['isIncremental'].upper() == "FALSE" else True
        controller.ingest_raw(isIncremental)
    else:
        logger.info("Iniciando carga da RAW para camada TRUSTED")
        controller.ingest_trusted()