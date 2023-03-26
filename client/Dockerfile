FROM python:3.10-alpine

RUN pip install --upgrade pip
RUN pip install pyyaml

COPY ./client/ /client
COPY ./client/config.yaml /config.yaml

ENTRYPOINT ["/bin/sh"]
