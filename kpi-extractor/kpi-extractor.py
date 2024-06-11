import os
import time
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

import psycopg2
import psycopg2.extensions

import json

from consumer import MessageProcessor, ReconnectingExampleConsumer

LOGGER = logging.getLogger(__name__)
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')   

# Load environment variables from the .env file
load_dotenv()
# Access environment variables
pg_user_env = os.getenv("POSTGRES_MANAGEMENT_USER")
pg_pw_env = os.getenv("POSTGRES_MANAGEMENT_PW")
pg_db_env = os.getenv("POSTGRES_MANAGEMENT_DB")

rabbitmq_url_env = os.getenv("AMQP_URL")
rabbitmq_user_env = os.getenv("RABBITMQ_MANAGEMENT_USER")
rabbitmq_pw_env = os.getenv("RABBITMQ_MANAGEMENT_PW")

# Timing
WAIT_UNTIL_START = 20 # seconds

# SQL statements
SQL_CREATE_LASTUPDATED_TABLE = \
    "CREATE TABLE IF NOT EXISTS lastupdated(" \
    "_id SERIAL PRIMARY KEY," \
    "time timestamp NOT NULL," \
    "deltaseconds INT NOT NULL," \
    "tablename text);"

class DB(MessageProcessor):
    def __init__(self, user, pw, db):
        try:
            self._conn = psycopg2.connect(
                 host="db_management",
                 database=db,
                 user=user,
                 password=pw
            )
            print("KPI extractor connected to postgreSQL")
            self._conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except Exception as e:
            print(f"Unable to connect to the database: {repr(e)}")
            exit(1)

        # Create table
        self.execute(SQL_CREATE_LASTUPDATED_TABLE)

        # Previous up'date'
        self._previous_update = None
 
    def execute(self, sql_code: str):
        with self._conn.cursor() as curs:
            curs.execute(sql_code)
        
    def process_message(self, msg):
        data = json.loads(msg.decode('utf-8'))
        timestamp_str = data.get("timestamp")
        timestamp_datetime = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f%z')
        delta_seconds = timedelta(seconds=0) \
            if self._previous_update is None \
            else (timestamp_datetime - self._previous_update).total_seconds()
        self._previous_update = timestamp_datetime

        tablename = data.get("table")
        sql_code = "INSERT INTO lastupdated (time, deltaseconds, tablename) VALUES(" \
            f"TO_TIMESTAMP('{timestamp_str}', 'YYYY-MM-DDTHH24:MI:SS.USTZH:TZM')," \
            f"{delta_seconds}," \
            f"'{tablename}');"
        LOGGER.info(f"Sending SQL to databse {self._conn.info.dbname}: {sql_code}")
        self.execute(sql_code)

    def close(self):
        self._conn.close()

def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Wait for DB and RabbitMQ initialization
    time.sleep(WAIT_UNTIL_START)

    # Connect to database
    db = DB(pg_user_env, pg_pw_env, pg_db_env)

    # Connect to RabbitMQ and start receiving messages
    consumer = ReconnectingExampleConsumer(rabbitmq_url_env,
                                           db)
    consumer.run()

    db.close()

if __name__ == '__main__':
    main()