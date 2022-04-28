#!/bin/bash
CURRENT_UID=`id -u`
CURRENT_GID=`id -g`

docker build -t ingest_framework .

rm -rf .venv  2> /dev/null
mkdir .venv 2> /dev/null

rm -rf build  2> /dev/null
mkdir build 2> /dev/null

rm -rf dist  2> /dev/null
mkdir dist 2> /dev/null

echo "Gerando .egg"
docker run --rm -v ${PWD}:/project/ ingest_framework bash -c "python3 setup.py bdist_egg"
if [ $? -ne 0 ]; then echo "Error getting the artifact from caontainer"; exit 1; fi;

