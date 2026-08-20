import sqlite3
from timetable import getLine
from datetime import datetime, time, timedelta
import orjson as json
import sys

db_path = './output/netex.db'

def frequencies(range):
    from_hour, from_min = list(map(int, range[0].split(':')[0:2]))
    to_hour, to_min = list(map(int, range[1].split(':')[0:2]))
    range_from =  timedelta(hours=from_hour, minutes=from_min)
    range_to =  timedelta(hours=to_hour, minutes=to_min)

    con = sqlite3.connect(db_path)

    cur = con.cursor()
    
    lines_query = cur.execute("""
SELECT id FROM lines
        """)
    
    lines = lines_query.fetchall()

    con.close()

    result = {}

    for line_id in lines:
        line_id = line_id[0]
        print(line_id)

        line_data = getLine(line_id)

        timetable = line_data['timetable']

        for direction_key in timetable:
            direction = timetable[direction_key]

            for quay_key in direction:
                quay = direction[quay_key]

                departures_per_day = {}

                for departure in quay:

                    if departure['departure'] is None: continue

                    for availability_key in departure['availabilities']:
                        availability = line_data['availabilities'][availability_key]

                        date_tracker = datetime.fromisoformat(availability['from'])
                        for bit in availability['bits']:
                            if bit == '1': 
                                hours, minutes, seconds = [float(val ) for val in line_data['journeys'][departure['journey']]['starting_time'].split(':')]
                                timestamp = date_tracker + timedelta(hours=hours, minutes=minutes, seconds=seconds) + timedelta(seconds=departure['departure'])
                                day = departures_per_day.setdefault(date_tracker.isoformat(), [])
                                if timestamp in day: raise Exception('Al in dag: ' + timestamp)
                                day.append(timestamp)

                            date_tracker = date_tracker + timedelta(days=1)

                for date in departures_per_day:
                    date_range_from = datetime.fromisoformat(date) + range_from
                    date_range_to = datetime.fromisoformat(date) + range_to

                    def range_filter(x): 
                        return x >= date_range_from and x < date_range_to

                    timestamps = departures_per_day[date]

                    in_range = len(list(filter(range_filter, timestamps)))

                    frequency = in_range ((range_to - range_from).total_seconds() / 3600)

                    result_line = result.setdefault(line_id, {})
                    result_direction = result_line.setdefault(direction_key, {})
                    result_quay = result_direction.setdefault(quay_key, {})
                    result_quay[date] = frequency

                    if frequency > 2:
                        open('./output/frequencies.json', 'wb').write(json.dumps(departures_per_day))
                        raise Exception('hoi')


        open('./output/frequencies.json', 'wb').write(json.dumps(result))

if __name__ == "__main__":
    if len(sys.argv) < 3: 
        print('usage: frequency.py hh:mm hh:mm')
        sys.exit(1)

    frequencies(sys.argv[1:3])