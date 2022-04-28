#!/bin/bash
PARAMETROS=$1
JOB_NAME=$2
DT_IMPORT=$3
IS_INCREMENTAL=$4
STEP=$5

if [ -z $1 ]
then
    echo "Parametros default"
    docker rm ingest -f && \
        docker run -t -p 8888:8888 -p 4040:4040 -v ~/.aws:/root/.aws:ro -v ${PWD}:/project/ \
        --name ingest ingest_framework /bin/bash /project/scripts/run.sh "parametros.json" "rent" "20210103" "FALSE" "trusted"
else
    echo "oxi"
    docker rm ingest -f && \
        docker run -t -p 8888:8888 -p 4040:4040 -v ~/.aws:/root/.aws:ro -v ${PWD}:/project/ \
        --name ingest ingest_framework /bin/bash /project/scripts/run.sh $PARAMETROS $JOB_NAME $DT_IMPORT $IS_INCREMENTAL $STEP
fi


