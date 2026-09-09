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

def getLines(secrets_file_path=None):
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

    query = """
SELECT lines.id, lines.code, brandings.name AS "branding", lines.name, number, transport_mode, transport_sub_mode, public_code,
 authorities.name AS "authority", authorities.code AS "authority_code", operators.name AS "operator", operators.code AS "operator_code", 
 product_types.name as "type_of_product", types_of_service.name AS "type_of_service", areas.name AS "network_name", 
 areas.code AS "network_code"
 FROM lines
 LEFT JOIN brandings ON brandings.id = branding
 LEFT JOIN authorities ON authorities.id = authority
 LEFT JOIN operators ON operators.id = operator
 LEFT JOIN types_of_service ON types_of_service.id = type_of_service
 LEFT JOIN rel_responsibility_area ON rel_responsibility_area.responsibility = responsibility_set
 LEFT JOIN areas ON areas.id = rel_responsibility_area.area_ref
 LEFT JOIN product_types ON product_types.id = type_of_product;
    """

    lines = list(map(
        lambda x: dict(zip(
            ("id", "code","branding","line_name","line_number","line_mode_of_transport","transport_sub_mode","public_code","authority","authority_code","operator","operator_code","type_of_product","type_of_service","network_name","network_code",),
            x
        )),
        querying.query_all(cur, query)
    ))

    lines_per_network = {}
    for line in lines:
        network = lines_per_network.setdefault(line['network_code'], {
            'id':line['network_code'],
            'name':line['network_name'],
            'parts':{}
        })
        part = network['parts'].setdefault('default', {
            "name":"default",
            "lines":[]
        })
        line['type'] = None
        if line['type_of_product'] is not None: line['type'] = line['type_of_product']
        elif line['branding'] is not None: line['type'] = line['branding']

        part['lines'].append(line)

    lines_per_network = list(lines_per_network.values())
    for network in lines_per_network:
        network['parts'] = list(network['parts'].values())


    cur.close()
    con.close()

    return lines_per_network
    # area / parts
    # code / line_name / line_number / mode_of_transport / type

def getLine(line_id = "", secrets_file_path=None):
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
        netex_db = sqlite3.connect('./output/netex.db')
        cur = netex_db.cursor()
        querying = SQLiteQuerying()
    
    line_query = """
SELECT lines.id, lines.code, lines.name AS "line_name", number AS "line_number", brandings.name AS "branding",
transport_mode AS "line_mode_of_transport", product_types.name as "type_of_product" FROM lines 
LEFT JOIN brandings ON brandings.id = branding
LEFT JOIN product_types ON product_types.id = type_of_product
WHERE
lines.id = %s;
    """
    journey_query = """
SELECT journeys.id, journeys.number, pattern,routes.id AS "route_id", lines.id AS "line_id", routes.direction, 
    lines.name AS "line_name", lines.number AS "line_number", realtime_info, starting_time, time_demand_type  FROM journeys
    INNER JOIN patterns ON patterns.id = pattern
    INNER JOIN routes ON routes.id = patterns.route
    INNER JOIN lines ON lines.id = routes.line
    WHERE lines.id = %s
;
    """
    availabilities_query = """
SELECT validity_conditions.* FROM validity_conditions 
    INNER JOIN availabilities_per_journey ON availabilities_per_journey.availability = validity_conditions.id
    INNER JOIN journeys ON availabilities_per_journey.journey = journeys.id
    WHERE journeys.id = %s
    """

    departures_query_old = """
SELECT journeys.id AS "journey", journeys.number, scheduled_stop_points.name, points_in_pattern.point_order AS "order", rel_stoppoint_quaycode.quay,
points_in_pattern.timing_point,
runtimes.time AS "runtime", waittimes.time AS "waittime" FROM journeys
INNER JOIN patterns ON patterns.id = journeys.pattern
INNER JOIN routes ON routes.id = patterns.route
INNER JOIN lines ON lines.id = routes.line
INNER JOIN points_in_pattern ON points_in_pattern.pattern = patterns.id
INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.id = points_in_pattern.stoppoint
INNER JOIN scheduled_stop_points ON scheduled_stop_points.id = points_in_pattern.stoppoint
LEFT JOIN runtimes ON runtimes.time_demand_type = journeys.time_demand_type AND
runtimes.timing_link = points_in_pattern.timing_link
LEFT JOIN waittimes ON waittimes.time_demand_type = journeys.time_demand_type AND
waittimes.timing_link = points_in_pattern.timing_link
WHERE lines.id = %s;
    """
    departures_query = """
SELECT journeys.id AS "journey", journeys.number, scheduled_stop_points.name, points_in_pattern.point_order AS "order", rel_stoppoint_quaycode.quay,
points_in_pattern.timing_point,
runtimes.time AS "runtime", waittimes.time AS "waittime", scheduled_stop_points.id AS scheduled_stop_point FROM journeys
INNER JOIN patterns ON patterns.id = journeys.pattern
INNER JOIN routes ON routes.id = patterns.route
INNER JOIN lines ON lines.id = routes.line
INNER JOIN points_in_pattern ON points_in_pattern.pattern = patterns.id
INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.id = points_in_pattern.stoppoint
INNER JOIN scheduled_stop_points ON scheduled_stop_points.id = points_in_pattern.stoppoint
LEFT JOIN runtimes ON runtimes.time_demand_type = journeys.time_demand_type AND
runtimes.timing_link = points_in_pattern.timing_link
LEFT JOIN waittimes ON waittimes.time_demand_type = journeys.time_demand_type AND
(waittimes.scheduled_stop_point = points_in_pattern.stoppoint OR waittimes.timing_point = points_in_pattern.timing_point)
WHERE lines.id = %s;
    """

    line_data = querying.query_one(cur, line_query, (line_id,))
    if not line_data: return {'error':f'geen lijn voor {line_id}'}

    line = dict(zip(
            ("id","code","line_name","line_number","branding","line_mode_of_transport","type_of_product",),
            line_data
    ))
    if line['type_of_product'] is not None: line['type'] = line['type_of_product']
    elif line['branding'] is not None: line['type'] = line['branding']
    line['notes'] = []

    journey_data = querying.query_all(cur, journey_query, (line_id,))
    if not journey_data: return {'error':f'geen ritten voor {line_id}'}

    journeys = list(map(
        lambda x: dict(zip(
            ("id","number","pattern","route_id","line_id","direction","line_name","line_number","realtime_info","starting_time","time_demand_type",),
            x
        )),
        journey_data
    ))

    departure_data = querying.query_all(cur, departures_query, (line_id,))
    if not departure_data: return {'error':f'geen vertrektijden voor {line_id}'}

    departure_list = list(map(
        lambda x: dict(zip(
            ("journey","number","name","order","quay","timing_point","runtime","waittime","scheduled_stop_point"),
            x
        )),
        departure_data
    ))

    notices_query = "SELECT * FROM notices WHERE notice_for IN %s"
    notice_data = querying.query_all(cur, notices_query, 
        (tuple(
            [line['id']] + 
            list(set(map(lambda x:x['id'], journeys))) +
            list(set(map(lambda x:x['scheduled_stop_point'], departure_list)))
        ),)
    )
    notices_per_id = {}
    notices_per_for = {}
    for notice_record in notice_data:
        notice = dict(zip(
            ('id','for','text'), notice_record
        ))
        notices_per_id[notice['id']] = notice_record
        for_list = notices_per_for.setdefault(notice['for'], [])
        for_list.append(notice['id'])

    if line['id'] in notices_per_for:
        line['notes'] = notices_per_for[line['id']]

    departures = {}
    for departure in departure_list:
        departures.setdefault(departure['journey'], []).append(departure)

    entry = {
            "line":line,
            "quays":{},
            "notes":notices_per_id,
            "availabilities":{},
            "vehicles":{},
            "timetable":{},
            "journeys":{}
        }

    for journey in journeys:
        availabilities = list(map(
            lambda x: dict(zip(
                ("id","from","through","bits",),
                x
            )),
            querying.query_all(cur, availabilities_query, (journey['id'],))
        ))

        entry['availabilities'] = entry['availabilities'] | dict([i['id'], i] for i in availabilities)

        direction = entry['timetable'].setdefault(journey['direction'], {})

        time_tracker = 0

        for departure in departures[journey['id']]:
            
            quay = direction.setdefault(departure['quay'], [])
            quay_in_entry = entry['quays'].setdefault(departure['quay'], {
                'quay_name':departure['name'],
                'quay_code':departure['quay'],
                'quay_location':None,
                'known_orders':{}
            })

            quay_direction_orders = quay_in_entry['known_orders'].setdefault(
                journey['direction'], {}
            )

            arrival = time_tracker

            if departure['waittime']:
                time_tracker = time_tracker + departure['waittime']
            
            departure_info = {
                'arrival':arrival,
                'departure':time_tracker,
                'order':departure['order'],
                'journey':journey['id'],
                'notes':[],
                'availabilities':[i['id'] for i in availabilities]
            }

            departure_order_count = quay_direction_orders.setdefault(str(departure['order']), 0)
            departure_order_count = departure_order_count + 1

            if departure['runtime']:
                time_tracker = time_tracker + departure['runtime']

            if departure['scheduled_stop_point'] in notices_per_for:
               departure_info['notes'] =  notices_per_for[departure['scheduled_stop_point']]

            quay.append(departure_info)

        vehicle_index = entry['vehicles'].setdefault('None', # journey['vehicle_type'] ,
            len(entry['vehicles']))
        
        notes = []
        if journey['id'] in notices_per_for:
            notes = notices_per_for[journey['id']]

        entry['journeys'][journey['id']] = {
            'number':journey['number'],
            'starting_time':journey['starting_time'],
            'route':journey['route_id'],
            'vehicle':vehicle_index,
            'notes':notes
        }

    cur.close()
    con.close()

    return entry

# Only Postgres support
def getDepartures(stopplace, timestamp=datetime.now(), secrets_file_path=None):
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
    

    availabilities_query = """
    SELECT validity_conditions.*, availabilities_per_journey.journey FROM availabilities_per_journey
    INNER JOIN (
	SELECT journeys.id AS journey,  stopplace, rel_quay_stopplace.quay FROM rel_quay_stopplace
	INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.quay = rel_quay_stopplace.quay
	INNER JOIN points_in_pattern ON points_in_pattern.stoppoint = rel_stoppoint_quaycode.id
	INNER JOIN patterns ON patterns.id = points_in_pattern.pattern
	INNER JOIN journeys ON journeys.pattern = patterns.id
    ) AS locations ON locations.journey = availabilities_per_journey.journey
    INNER JOIN validity_conditions ON validity_conditions.id = availabilities_per_journey.availability
    WHERE locations.stopplace = %s AND
    available_from <= %s AND available_through >= %s;
    """
    timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)

    availabilities = querying.query_all(cur, availabilities_query, (stopplace, timestamp, timestamp))


    journey_ids = []

    for availability in availabilities:
        period = {
            'from':availability[1],
            'through':availability[2],
            'bits':availability[3]
        }
        if not period['from'] or not period['through']: continue
        if not period['from'].tzinfo: period['from'] = period['from'].replace(tzinfo=tz)
        if not period['through'].tzinfo: period['through'] = period['through'].replace(tzinfo=tz)

        journey_id = availability[4]

        diff = (timestamp - period['from']).days

        if period['bits'][diff] == '1':
            journey_ids.append(journey_id)


    if len(journey_ids) == 0: 
        print('Geen ritten')
        return {}

    journeys_query = """
    SELECT lines.id AS line_id, lines.code AS line_code, routes.direction, journeys.id, journeys.number,
    journeys.pattern, lines.number AS line_number, lines.name AS "line_name", (
		SELECT name FROM brandings WHERE brandings.id = lines.branding
	) branding, 
    lines.transport_mode, lines.transport_sub_mode, lines.public_code, (
		SELECT name FROM authorities WHERE authorities.id = lines.authority
	) authority, 
    (
		SELECT name FROM operators WHERE operators.id = lines.operator
	) operator, (
		SELECT name FROM product_types WHERE product_types.id = lines.type_of_product
	) type_of_product, patterns_and_displays.name, patterns_and_displays.front, patterns_and_displays.side, journeys.starting_time, (SELECT code FROM datasources WHERE datasources.id = lines.datasource_code) datasource
    FROM journeys
    INNER JOIN (
		SELECT patterns.id AS pattern_id, patterns.route, destination_displays.* FROM patterns
		LEFT JOIN destination_displays ON destination_displays.id = patterns.destination_display
	) AS patterns_and_displays ON patterns_and_displays.pattern_id = journeys.pattern
    INNER JOIN routes ON routes.id = patterns_and_displays.route
    INNER JOIN lines ON lines.id = routes.line
    WHERE journeys.id IN %s
    """

    journey_ids = tuple(journey_ids)

    journey_details = querying.query_all(cur, journeys_query, (journey_ids,))

    planned_journeys = {}
    scheduled_stop_points = {}

    for journey in journey_details:
        planned_journey = {
            'Line':journey[0],
            'LineCode':journey[1],
            'Direction':journey[2],
            'DatedVehicleJourney':journey[3],
            'DatedVehicleJourneyCode':journey[4],
            'JourneyPattern':journey[5],
            'PublishedLineName':journey[6],
            'LineName':journey[7],
            'Branding':journey[8],
            'TransportMode':journey[9],
            'TransportSubMode':journey[10],
            'LinePublicCode':journey[11],
            'Authority':journey[12],
            'Operator':journey[13],
            'TypeOfProduct':journey[14],
            'DestinationDisplay':journey[15],
            # 'DestinationDisplayOnBus':{
            #     'Front':journey[16],
            #     'Side':journey[17]
            # },
            'StartingTime':journey[18],
            'DataSourceCode':journey[19],
            'Calls':{},
        }

        planned_journeys[planned_journey['DatedVehicleJourney']] = planned_journey

    departures_query = """SELECT journeys.id AS "journey", scheduled_stop_points.id AS scheduled_stop_point, scheduled_stop_points.name, points_in_pattern.point_order AS "order", rel_stoppoint_quaycode.quay,
    points_in_pattern.timing_point, runtimes.time AS "runtime", 
    waittimes.time AS "waittime", (SELECT stopplace FROM rel_quay_stopplace WHERE rel_quay_stopplace.quay = rel_stoppoint_quaycode.quay) stopplace
    FROM journeys
    INNER JOIN patterns ON patterns.id = journeys.pattern
    INNER JOIN routes ON routes.id = patterns.route
    INNER JOIN lines ON lines.id = routes.line
    INNER JOIN points_in_pattern ON points_in_pattern.pattern = patterns.id
    LEFT JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.id = points_in_pattern.stoppoint
    LEFT JOIN scheduled_stop_points ON scheduled_stop_points.id = points_in_pattern.stoppoint
    LEFT JOIN runtimes ON runtimes.time_demand_type = journeys.time_demand_type AND
    runtimes.timing_link = points_in_pattern.timing_link
    LEFT JOIN waittimes ON waittimes.time_demand_type = journeys.time_demand_type AND
    (waittimes.scheduled_stop_point = points_in_pattern.stoppoint OR waittimes.timing_point = points_in_pattern.timing_point)
    WHERE journeys.id IN %s
    ORDER BY journey, points_in_pattern.point_order;
    """

    departures = querying.query_all(cur, departures_query, (journey_ids,))
    departures_per_journey = {}
    for departure in departures: 
        departures_per_journey.setdefault(departure[0], []).append(departure)

        # notices_query = """GET notices.* FROM notices
        # WHERE notice_for IN %s"""

    for journey_id in departures_per_journey:
        journey = departures_per_journey[journey_id]
        if not journey_id in planned_journeys: continue

        departure_time_parts = list(map(int, planned_journeys[journey_id]['StartingTime'].split(':')))
        time_tracker = timestamp.replace(
            hour=departure_time_parts[0],
            minute=departure_time_parts[1],
            second=departure_time_parts[2],
        )

        calls = []

        for departure in journey:
            index = departure[3]

            if departure[1] is None:
                runtime = departure[6]
                waittime = departure[7]
                if waittime: time_tracker += timedelta(seconds=waittime)
                if runtime: time_tracker += timedelta(seconds=runtime)
                continue

            departure_data = {
                'StopPoint':departure[1],
                'AimedArrivalTime':None,
                'AimedDepartureTime':None
            }

            if index != 0:
                departure_data['AimedArrivalTime'] = time_tracker.isoformat()


            if not departure_data['StopPoint'] in scheduled_stop_points:
                scheduled_stop_points[departure_data['StopPoint']] = {
                    'Name':departure[2],
                    'Quay':departure[4],
                    'StopPlace':departure[8],
                }

            runtime = departure[6]
            waittime = departure[7]

            if waittime: time_tracker += timedelta(seconds=waittime)

            if index + 1 < len(journey):
                departure_data['AimedDepartureTime'] = time_tracker.isoformat()

            if runtime: time_tracker += timedelta(seconds=runtime)

            # if len(calls) < index + 1:
            #     print(f'{journey_id}: {str(index)} {str(len(calls))}')
            calls.append(departure_data)

        planned_journeys[journey_id]['Calls'] = calls


    notice_able_ids = set()
    for journey_id in planned_journeys:
        notice_able_ids.union((journey_id, planned_journeys[journey_id]['Line']))
    for departure in departures:
        notice_able_ids.add(departure[1])

    notices_query = "SELECT * FROM notices WHERE notice_for IN %s"
    notice_data = querying.query_all(cur, notices_query, (tuple(notice_able_ids),))
    notices_per_id = {}
    notices_per_for = {}
    for notice_record in notice_data:
        notice = dict(zip(
            ('id','for','text'), notice_record
        ))
        notices_per_id[notice['id']] = notice_record
        for_list = notices_per_for.setdefault(notice['for'], [])
        for_list.append(notice['id'])
    

    return {
        'scheduled_stop_points':scheduled_stop_points,
        'journeys':planned_journeys,
        'notices':notices_per_id,
        'notice_assignments':notices_per_for
    }


if __name__ == "__main__":

    if len(sys.argv) > 2:
        d = getDepartures(sys.argv[2])
        open('./output/departures.json', 'wb').write(json.dumps(d))


"""
SELECT * FROM validity_conditions WHERE available_from <= '2026-09-04T14:41:11.854594' AND available_through >= '2026-09-04T14:41:11.854594';
SELECT availabilities_per_journey.*, locations.stopplace, locations.quay FROM availabilities_per_journey

INNER JOIN (
	SELECT journeys.id AS 'journey',  stopplace, rel_quay_stopplace.quay FROM rel_quay_stopplace
	INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.quay = rel_quay_stopplace.quay
	INNER JOIN points_in_pattern ON points_in_pattern.stoppoint = rel_stoppoint_quaycode.id
	INNER JOIN patterns ON patterns.id = points_in_pattern.pattern
	INNER JOIN journeys ON journeys.pattern = patterns.id
) AS locations ON locations.journey = availabilities_per_journey.journey

WHERE locations.quay = 'NL:Q:40221200'


SELECT validity_conditions.*, locations.* FROM availabilities_per_journey

INNER JOIN (
	SELECT journeys.id AS journey,  stopplace, rel_quay_stopplace.quay FROM rel_quay_stopplace
	INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.quay = rel_quay_stopplace.quay
	INNER JOIN points_in_pattern ON points_in_pattern.stoppoint = rel_stoppoint_quaycode.id
	INNER JOIN patterns ON patterns.id = points_in_pattern.pattern
	INNER JOIN journeys ON journeys.pattern = patterns.id
) AS locations ON locations.journey = availabilities_per_journey.journey
INNER JOIN validity_conditions ON validity_conditions.id = availabilities_per_journey.availability
WHERE locations.quay = 'NL:Q:40221200' AND
available_from <= '2026-09-04T14:41:11.854594' AND available_through >= '2026-09-04T14:41:11.854594';
"""