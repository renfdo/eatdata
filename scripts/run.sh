#!/bin/bash
PARAMETROS=$1
JOB_NAME=$2
DT_IMPORT=$3
IS_INCREMENTAL=$4
STEP=$5

sh /home/spark-2.4.3-bin-spark-2.4.3-bin-hadoop2.8/bin/spark-submit app.py \
--parametros $PARAMETROS \
--job $JOB_NAME \
--dtimport $DT_IMPORT \
--isIncremental $IS_INCREMENTAL \
--step $STEP
