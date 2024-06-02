FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install python3 python3-pip -y
RUN pip3 install --upgrade pip
WORKDIR /app

COPY postgres-rabbitmq-bridge/requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

COPY postgres-rabbitmq-bridge/postgres-rabbitmq-bridge.py /app
COPY ./.env /app
COPY postgres-rabbitmq-bridge/trigger_function.sql /app
COPY postgres-rabbitmq-bridge/trigger_installation_macro.sql /app

CMD ["python3", "-u", "postgres-rabbitmq-bridge.py"]