FROM python:3.10-alpine

RUN pip install --upgrade pip
RUN pip install pyyaml

COPY .data/dataset.zip /dataset.zip
RUN mkdir /data && unzip /dataset.zip -d /data && rm /dataset.zip

COPY ./client/ /client
COPY ./client/config.yaml /config.yaml

ENTRYPOINT ["/bin/sh"]
