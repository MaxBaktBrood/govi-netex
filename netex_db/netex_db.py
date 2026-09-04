import os
import orjson as json
import psycopg2
import typing
import sqlite3

def get_pg_con(secrets_file=None):
    if os.path.exists('./secrets.json') or secrets_file is not None:
        if secrets_file is None:
            secrets_file = json.loads(
                open('secrets.json', 'r').read()
            )

        if 'POSTGRES_credentials' in secrets_file:
            if not ('POSTGRES_available' in secrets_file and secrets_file['POSTGRES_available'] is False):

                credential_string = ""
                for key in secrets_file['POSTGRES_credentials']:
                    credential_string += f"{key}={str(secrets_file['POSTGRES_credentials'][key])} "

                con = psycopg2.connect(credential_string)

                return (con, credential_string)
            else: return None
        else: return None
    else: return None

class SQLiteQuerying:
    def query_all(self, cur: sqlite3.Cursor, q, params=()):
        return cur.execute(q, params).fetchall()
    def query_one(self, cur: sqlite3.Cursor, q, params=()):
        return cur.execute(q, params).fetchone()
    
    def __init__(self):
        pass

class PostgresQuerying:
    def query_all(self, cur, q, params=()):
        cur.execute(q, params)
        return cur.fetchall()
    def query_one(self, cur, q, params=()):
        cur.execute(q, params)
        return cur.fetchone()



