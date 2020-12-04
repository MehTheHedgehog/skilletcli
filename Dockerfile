FROM python:3-buster

COPY . /skilletcli
WORKDIR /skilletcli

RUN pip install -r requirements.txt
