import os
import orjson as json
import psycopg2
import typing
import sqlite3

def get_pg_con(secrets=None, secrets_file_path='./secrets.json'):
    if os.path.exists(secrets_file_path) or secrets is not None:
        if secrets is None:
            secrets = json.loads(
                open(secrets_file_path, 'r').read()
            )
    
        if 'POSTGRES_credentials' in secrets:
            if not ('POSTGRES_available' in secrets and secrets['POSTGRES_available'] is False):

                credential_string = ""
                for key in secrets['POSTGRES_credentials']:
                    credential_string += f"{key}={str(secrets['POSTGRES_credentials'][key])} "

                con = psycopg2.connect(credential_string)
                
                return (con, credential_string)
            else: return None
        else: return None
    else: return None

class SQLiteQuerying:
    def query_all(self, cur: sqlite3.Cursor, q, params=()):
        return cur.execute(q.replace('%s', '?'), params).fetchall()
    def query_one(self, cur: sqlite3.Cursor, q, params=()):
        return cur.execute(q.replace('%s', '?'), params).fetchone()
    
    def __init__(self):
        pass

class PostgresQuerying:
    def query_all(self, cur, q, params=()):
        cur.execute(q, params)
        return cur.fetchall()
    def query_one(self, cur, q, params=()):
        cur.execute(q, params)
        return cur.fetchone()


