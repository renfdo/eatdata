## .devcontainer/Dockerfile
FROM python:3.8

RUN mkdir /project
WORKDIR /project

RUN python3 -m pip install --upgrade pip wheel setuptools && \
    python3 -m pip cache purge

COPY ./requirements.txt /project/

RUN pip install -r /project/requirements.txt
