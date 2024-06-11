import datetime
import os
import time
import json
import random
import psycopg2

from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv()
# Access environment variables
user_env = os.getenv("POSTGRES_USER")
pw_env = os.getenv("POSTGRES_PW")
db_env = os.getenv("POSTGRES_DB")

# Timing
WAIT_UNTIL_START = 30 # seconds
MIN_UPDATE_INTERVAL = 3  # seconds
MAX_UPDATE_INTERVAL = 15  # seconds

class DB:
    def __init__(self, user, pw, db):
        try:
            self._conn = psycopg2.connect(
                 host="db",
                 database=db,
                 user=user,
                 password=pw
            )
            self._conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except:
            print("Unable to connect to the database")
            exit(1)
 
    def execute(self, sql_code: str):
        with self._conn.cursor() as curs:
            curs.execute(sql_code)
    
    def add_patient(self, patient: dict, update_instead_of_insert: bool):
        # Translate dates and strings into appropriate format
        p = patient.copy()
        for k, v in p.items():
            if isinstance(v, datetime.date):
                datestr = v.strftime("%Y-%m-%d")
                p[k] = f"DATE '{datestr}'"
            if isinstance(v, str):
                p[k] = f"'{v}'"
        # Now build and execute the SQL statement
        if update_instead_of_insert:
            # Handle (unique) primary key
            where_key_value = f"_patientid={p.get('_patientid')}"
            p.pop("_patientid")
            # Create key=value pairs for all other columns
            keys_and_values = ",".join([f"{k}={str(v)}" for k,v in p.items()])
            sql_code = f"UPDATE patient SET {keys_and_values} WHERE {where_key_value}"
        else:
            sql_code = f"INSERT INTO patient ({','.join(p.keys())}) "\
                       f"VALUES ({','.join(map(str, p.values()))})"
        self.execute(sql_code)

# Helper function for json load of date value
def date_hook(json_dict):
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.datetime.strptime(value, "%Y-%m-%d")
        except:
            pass
    return json_dict

if __name__ == "__main__":
    # Wait for DB and bridge initialization
    time.sleep(WAIT_UNTIL_START)

    # Connect to database
    db = DB(user_env, pw_env, db_env)

    # Delete patient table contents
    db.execute('DELETE FROM patient')

    update_instead_of_insert = False
    while(True):
        # Read json patient file contents and add it to the database
        with open('patients.json') as json_file:
            patients = json.load(json_file, object_hook=date_hook)
            for patient in patients:
                if update_instead_of_insert:
                    print(f"Updating record: {patient}")
                else:
                    print(f"Adding record: {patient}")
                db.add_patient(patient, update_instead_of_insert)
                time.sleep(
                    random.randint(MIN_UPDATE_INTERVAL,MAX_UPDATE_INTERVAL))

        # After the first round, UPDATE instead of INSERT INTO
        update_instead_of_insert = True

    print('done')