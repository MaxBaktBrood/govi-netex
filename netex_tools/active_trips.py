import sqlite3
from os import path 
import orjson as json
import sys
if __name__ == "__main__":
    if len(sys.argv) < 1: raise Exception('geef een pad op')
    sys.path.append(sys.argv[1])
from netex_db.netex_db import get_pg_con, PostgresQuerying, SQLiteQuerying
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
tz = ZoneInfo(time.tzname[0])


def active_trips(secrets_file_path = None):
    con = None
    cur = None
    querying = None

    postgres_con = get_pg_con(secrets_file_path=secrets_file_path)
    if postgres_con is not None: 
        con = postgres_con[0]
        cur = con.cursor()
        querying = PostgresQuerying()
    else:
        if not path.exists('./output/netex.db'): return []
        con = sqlite3.connect('./output/netex.db')
        cur = con.cursor()
        querying = SQLiteQuerying()

    availabilities_query = """
    SELECT * FROM validity_conditions WHERE id IN (
        SELECT availability FROM availabilities_per_journey
        WHERE availabilities_per_journey.availability = validity_conditions.id
    )
    """

    availability_dates = {}

    for availability in querying.query_all(cur, availabilities_query):
        dates = availability_dates.setdefault(availability[0], [])
        period = {
            'from':availability[1],
            'through':availability[2],
            'bits':availability[3],
            'is_available':availability[4]
        }
        if not period['from'] or not period['through']: continue
        if not period['from'].tzinfo: period['from'] = period['from'].replace(tzinfo=tz)
        if not period['through'].tzinfo: period['through'] = period['through'].replace(tzinfo=tz)

        for bit in availability['bits']


