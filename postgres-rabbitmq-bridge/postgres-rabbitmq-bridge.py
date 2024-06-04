import os
import time

import select
import psycopg2
import psycopg2.extensions

import pika
import json

from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv()
# Access environment variables
pg_user_env = os.getenv("POSTGRES_USER")
pg_pw_env = os.getenv("POSTGRES_PW")
pg_db_env = os.getenv("POSTGRES_DB")

rabbitmq_url_env = os.getenv("AMQP_URL")
rabbitmq_user_env = os.getenv("RABBITMQ_USER")
rabbitmq_pw_env = os.getenv("RABBITMQ_PW")

# Timing
WAIT_UNTIL_START = 20 # seconds


class DB:
    def __init__(self, user, pw, db):
        try:
            self._conn = psycopg2.connect(
                 host="db",
                 database=db,
                 user=user,
                 password=pw
            )
            print("Bridge connected to postgreSQL")
            self._conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except Exception as e:
            print(f"Unable to connect to the database: {repr(e)}")
            exit(1)

        with self._conn.cursor() as curs:
            # Find all table names
            curs.execute("SELECT tablename FROM pg_catalog.pg_tables " \
                                "WHERE schemaname != 'pg_catalog' AND " \
                                "schemaname != 'information_schema';")
            # result is list of tuples; we need the first tuple elements
            table_names = [t[0] for t in curs.fetchall()]

            # Install trigger function
            with open('trigger_function.sql', 'r') as file:
                sql_code = file.read()
                curs.execute(sql_code)

            # Install trigger for all tables
            with open('trigger_installation_macro.sql', 'r') as file:
                installation_macro = file.read()
                for table in table_names:
                    sql_code = installation_macro.replace("$TABLE$", table)
                    curs.execute(sql_code)

            # Start listening to table_changed notifications
            curs.execute("LISTEN table_changed;")

class RabbitMQ:
    def __init__(self, user, pw):
        try:
            #credentials = pika.PlainCredentials(user, pw)
            #parameters = pika.ConnectionParameters(
            #    host='rmq0',
            #    port=15672,
            #    virtual_host='/',
            #    credentials=credentials)
            url_params = pika.URLParameters(rabbitmq_url_env)
            self._conn = pika.BlockingConnection(url_params)
            print("Bridge connected to rabbitmq")

            self._chan_newpatient = self._conn.channel()
            self._chan_newpatient.queue_declare(queue='newpatient')

            self._chan_latestupdate = self._conn.channel()
            self._chan_latestupdate.queue_declare(queue='latestupdate')

        except Exception as e:
            print(f"Unable to connect to the rabbitmq: {repr(e)}")
            exit(2)

    def publish_new_patient(self, msg: str):
        self._chan_newpatient.basic_publish(
            exchange='',
            routing_key='newpatient',
            body=msg)

    def publish_latest_update(self, msg: str):
        self._chan_latestupdate.basic_publish(
            exchange='',
            routing_key='latestupdate',
            body=msg)

if __name__ == "__main__":
    # Wait for DB and RabbitMQ initialization
    time.sleep(WAIT_UNTIL_START)

    # Connect to database
    db = DB(pg_user_env, pg_pw_env, pg_db_env)

    # Connect to RabbitMQ
    rabbit = RabbitMQ(rabbitmq_user_env, rabbitmq_pw_env)

    while True:
        if select.select([db._conn],[],[],5) == ([],[],[]):
            print("Timeout")
        else:
            db._conn.poll()
            while db._conn.notifies:
                notify = db._conn.notifies.pop(0)
                print("Got NOTIFY:", notify.pid, notify.channel, notify.payload)

                msg = json.loads(notify.payload)

                # If new patient, send that message
                if msg.get("operation") == "INSERT" and \
                    msg.get("table") == "patient":
                    record = msg.get("new_record")
                    patientid = record.get("_patientid")
                    timestamp = record.get("timestamp")
                    rabbitmq_msg = {'patientid': patientid,
                                    'timestamp': timestamp}
                    rabbit.publish_new_patient(json.dumps(rabbitmq_msg))

                # Send latest update message
                table = msg.get("table")
                record = msg.get("new_record")
                timestamp = record.get("timestamp")
                rabbitmq_msg = {'table': table,
                                'timestamp': timestamp}
                rabbit.publish_latest_update(json.dumps(rabbitmq_msg))
