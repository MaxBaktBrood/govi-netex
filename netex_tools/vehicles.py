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

def getVehicles(vehicle_numbers, timestamp=None, secrets_file_path=None):
    if not timestamp: timestamp = datetime.now()

    con = None
    cur = None
    querying = None

    postgres_con = get_pg_con(secrets_file_path=secrets_file_path)
    if postgres_con is not None: 
        con = postgres_con[0]
        cur = con.cursor()
        querying = PostgresQuerying()
    else:
        return None

    query = """
    SELECT vehicles.id, vehicles.operational_number, vehicles.datasource_code, vehicle_types.name, vehicle_types.length, brandings.name FROM vehicles 
    LEFT JOIN vehicle_types ON  vehicle_types.id = vehicles.vehicle_type
    LEFT JOIN brandings ON  brandings.id = vehicle_types.branding
    WHERE
    datasource_code||':'||operational_number IN %s AND
    (valid_from IS NULL OR valid_from <= %s) AND (valid_through IS NULL OR valid_through >= %s);
    """
    timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)

    vehicles = list(map(
        lambda x: dict(zip(
            ("id", "operational_number","datasource_code", "vehicle_type_name", "length", "branding_name"),
            x
        )),
        querying.query_all(cur, query, (vehicle_numbers, timestamp, timestamp))
    ))

    return dict(list(map(
        lambda x: (":".join([x['datasource_code'], x['operational_number']]), x,), vehicles
    )))



if __name__ == "__main__":

    if len(sys.argv) > 2:
        d = getDepartures(sys.argv[2])
        open('./output/departures.json', 'wb').write(json.dumps(d))