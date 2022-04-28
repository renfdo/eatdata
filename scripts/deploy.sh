#!/bin/bash
ACCOUNT=$1
DOMAIN=$2
ENV=$3


if [ -z $ACCOUNT ]
then
    echo "Account variable needed"
    exit 1
fi

if [ -z $DOMAIN ]
then
    echo "Domain variable needed"
    exit 1
fi

if [ -z $ENV ]
then
    echo "Env variable needed"
    exit 1
fi


echo "Create docker image"
./scripts/build-docker.sh


rm -rf tmp  2> /dev/null
mkdir tmp 2> /dev/null

# vai fazer enviar para o s3
for entry in "${PWD}"/*
do
    DICT=${entry:${#entry}-3:${#entry}}
    if [ "$DICT" != "tmp" ];
    then
        echo $entry
        cp -r "$entry" tmp
    fi
done

# remove pasta desnecessárias
rm -rf tmp/.venv
rm -rf tmp/.__pycache__
rm -rf tmp/landing
rm -rf tmp/output
rm -rf tmp/scripts

# envia para o s3
echo "Enviando para o bucket artifact"
echo "aws s3 cp tmp s3://multlake-$ACCOUNT-$DOMAIN-$ENV-artifact/glue_scripts/ --recursive"

aws s3 cp tmp s3://multlake-$ACCOUNT-$DOMAIN-$ENV-artifact/glue_scripts/ --recursive
if [ $? -ne 0 ]; then echo "erro ao enviar para o s3"; exit 1; fi;

rm -rf tmp  2> /dev/null