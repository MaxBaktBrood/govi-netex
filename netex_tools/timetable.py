import sqlite3
from os import path

def getLines():
    if not path.exists('./output/netex.db'): return []
    netex_db = sqlite3.connect('./output/netex.db')
    cur = netex_db.cursor()

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
        cur.execute(query).fetchall()
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
    netex_db.close()

    return lines_per_network
    # area / parts
    # code / line_name / line_number / mode_of_transport / type

def getLine(line_id = ""):
    if not path.exists('./output/netex.db'): return {'error':'geen database'}
    netex_db = sqlite3.connect('./output/netex.db')
    cur = netex_db.cursor()
    line_query = """
SELECT lines.code, lines.name AS "line_name", number AS "line_number", brandings.name AS "branding",
transport_mode AS "line_mode_of_transport", product_types.name as "type_of_product" FROM lines 
LEFT JOIN brandings ON brandings.id = branding
LEFT JOIN product_types ON product_types.id = type_of_product
WHERE
lines.id = ?;
    """
    journey_query = """
SELECT journeys.id, journeys.number, pattern,routes.id AS "route_id", lines.id AS "line_id", routes.direction, 
    lines.name AS "line_name", lines.number AS "line_number", realtime_info, starting_time, time_demand_type  FROM journeys
    INNER JOIN patterns ON patterns.id = pattern
    INNER JOIN routes ON routes.id = patterns.route
    INNER JOIN lines ON lines.id = routes.line
    WHERE lines.id = ?
;
    """
    availabilities_query = """
SELECT validity_conditions.* FROM validity_conditions 
    INNER JOIN availabilities_per_journey ON availabilities_per_journey.availability = validity_conditions.id
    INNER JOIN journeys ON availabilities_per_journey.journey = journeys.id
    WHERE journeys.id = ?
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
WHERE lines.id = ?;
    """
    departures_query = """
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
(waittimes.scheduled_stop_point = points_in_pattern.stoppoint OR waittimes.timing_point = points_in_pattern.timing_point)
WHERE lines.id = ?;
    """

    line_data = cur.execute(line_query, (line_id,)).fetchone()
    if not line_data: return {'error':f'geen lijn voor {line_id}'}

    line = dict(zip(
            ("code","line_name","line_number","branding","line_mode_of_transport","type_of_product",),
            line_data
    ))
    if line['type_of_product'] is not None: line['type'] = line['type_of_product']
    elif line['branding'] is not None: line['type'] = line['branding']
    line['notes'] = {}

    journey_data = cur.execute(journey_query, (line_id,)).fetchall()
    if not journey_data: return {'error':f'geen ritten voor {line_id}'}

    journeys = list(map(
        lambda x: dict(zip(
            ("id","number","pattern","route_id","line_id","direction","line_name","line_number","realtime_info","starting_time","time_demand_type",),
            x
        )),
        journey_data
    ))

    departure_data = cur.execute(departures_query, (line_id,)).fetchall()
    if not departure_data: return {'error':f'geen vertrektijden voor {line_id}'}

    departure_list = list(map(
        lambda x: dict(zip(
            ("journey","number","name","order","quay","timing_point","runtime","waittime",),
            x
        )),
        departure_data
    ))

    departures = {}
    for departure in departure_list:
        departures.setdefault(departure['journey'], []).append(departure)

    entry = {
            "line":line,
            "quays":{},
            "notes":{},
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
            cur.execute(availabilities_query, (journey['id'],)).fetchall()
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

            quay.append(departure_info)

        vehicle_index = entry['vehicles'].setdefault('None', # journey['vehicle_type'] ,
            len(entry['vehicles']))

        entry['journeys'][journey['id']] = {
            'number':journey['number'],
            'starting_time':journey['starting_time'],
            'route':journey['route_id'],
            'vehicle':vehicle_index
        }

    cur.close()
    netex_db.close()

    return entry
