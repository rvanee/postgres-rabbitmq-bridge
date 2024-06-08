FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install python3 python3-pip -y
RUN pip3 install --upgrade pip
WORKDIR /app

COPY kpi-extractor/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY kpi-extractor/kpi-extractor.py /app
COPY kpi-extractor/consumer.py /app
COPY ./.env /app

CMD ["python3", "-u", "kpi-extractor.py"]