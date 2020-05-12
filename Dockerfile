FROM python:3-alpine

RUN pip install docker falcon pyyaml jinja2
CMD python3 cimme.py

WORKDIR /code
COPY cimme.py /code/main.py
