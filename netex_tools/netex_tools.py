import sqlite3
import geopandas
import orjson as json


db_path = './output/netex.db'

def lines_geodata(mode="shp"):
    con = sqlite3.connect(db_path)

    cur = con.cursor()

    lines_query = cur.execute("""
SELECT route as id, lines.id as "line_id", lines.number as "line_number", lines.name as "line_name",
lines.code as "line_code", direction, lines.transport_mode as "mode_of_transport", 
lines.transport_sub_mode as "sub_mode_of_transport", brandings.name as "formula",
product_types.name as "type_of_product", authorities.name as "authority", authorities.code as "authority_code",
operators.name as "operator", operators.code as "operator_code", areas.name as "network",
areas.id as "network_id", areas.code as "network_code", lines.type_of_service, lines.custom_category,
group_concat(routelinks.location, " ") as geodata
FROM rel_point_route
LEFT JOIN routelinks ON rel_point_route.link = routelinks.id
INNER JOIN routes ON routes.id = rel_point_route.route
LEFT JOIN lines ON lines.id = routes.line
LEFT JOIN brandings ON brandings.id = lines.branding
LEFT JOIN rel_responsibility_area ON rel_responsibility_area.responsibility = lines.responsibility_set
LEFT JOIN areas ON areas.id = rel_responsibility_area.area_ref
LEFT JOIN authorities ON authorities.id = lines.authority
LEFT JOIN operators ON operators.id = lines.operator
LEFT JOIN product_types ON product_types.id = lines.type_of_product
--product service responsibility_set
GROUP BY route
    """)

    lines = lines_query.fetchall()

    con.close()

    for line in lines:
        coords = line[19].split(" ")

        json_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [coords[x + x], coords[x + x + 1]] for x in range(int(len(coords) / 2))
                ]
            },
            "properties": dict(
                (
                ('id', line[0]),
                ('line_id', line[1]),
                ('line_number', line[2]),
                ('line_name', line[3]),
                ('line_code', line[4]),
                ('direction', line[5]),
                ('mode_of_transport', line[6]),
                ('sub_mode_of_transport', line[7]),
                ('formula', line[8]),
                ('type_of_product', line[9]),
                ('authority', line[10]),
                ('authority_code', line[11]),
                ('operator', line[12]),
                ('operator_code', line[13]),
                ('network', line[14]),
                ('network_id', line[15]),
                ('network_code', line[16]),
                ('type_of_service', line[17]),
                ('custom_category', line[18]),
                )
            )
        }
        if mode == 'shp':
            geopandas.GeoDataFrame.from_features({
                'type':'FeatureCollection',
                'features':[json_feature]
            }).to_file('./output/lines.shp', mode='a')
        if mode == 'gpkg':
            geopandas.GeoDataFrame.from_features({
                'type':'FeatureCollection',
                'features':[json_feature]
            }).to_file('./output/lines.gpkg', driver='gpkg', mode='a')


def loom():
    con = sqlite3.connect(db_path)
    
    cur = con.cursor()

    stopplaces_query = cur.execute("""
SELECT stopplaces.* from stopplaces
    """)

    stopplaces = stopplaces_query.fetchall()

    lines_query = cur.execute(
        """
SELECT pip.pattern, pip.point_order, CASE WHEN stoppoint IS NOT NULL THEN 'stoppoint' WHEN timing_point IS NOT NULL THEN 'timing_point' ELSE NULL END AS "point",
pip.line_id, pip.line_label, stopplace ,CONCAT(tp_routepoint, ssp_routepoint) as "routepoint_2", routelinks.location FROM (
SELECT pip.pattern, pip.point_order, pip.stoppoint, pip.timing_point, lines.id as "line_id", lines.number as "line_label",
(
SELECT rel_timing_route_points.routepoint FROM rel_timing_route_points
LEFT JOIN patterns ON patterns.id = pip.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN rel_point_route ON rel_point_route.route = routes.id AND rel_point_route.point = rel_timing_route_points.routepoint
WHERE rel_timing_route_points.id = pip.timing_point
) tp_routepoint,
(
SELECT scheduled_stop_points.route_point FROM scheduled_stop_points
LEFT JOIN patterns ON patterns.id = pip.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN rel_point_route ON rel_point_route.route = routes.id AND rel_point_route.point = scheduled_stop_points.route_point
WHERE scheduled_stop_points.id = pip.stoppoint
) ssp_routepoint,
(
SELECT rel_quay_stopplace.stopplace FROM scheduled_stop_points
LEFT JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.stoppoint = scheduled_stop_points.id
LEFT JOIN rel_quay_stopplace ON rel_quay_stopplace.quay = rel_stoppoint_quaycode.quay
WHERE scheduled_stop_points.id = pip.stoppoint
) stopplace
FROM points_in_pattern pip
LEFT JOIN patterns ON patterns.id = pip.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN lines ON lines.id = routes.line
) AS pip
LEFT JOIN patterns ON patterns.id = pip.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN rel_point_route ON rel_point_route.route = routes.id AND rel_point_route.point = routepoint_2
LEFT JOIN routelinks ON routelinks.id = rel_point_route.link
ORDER BY pip.pattern AND pip.point_order
        """
    )

    links = lines_query.fetchall()
    con.close()

    grouped_links = {}

    for link in links:
        group = grouped_links.setdefault(link[0], [])
        group.append(link)

    result = {
        "type": "FeatureCollection",
        "features": []
    }

    links = {}

    for group_key in grouped_links:
        
        group = sorted(grouped_links[group_key], key=lambda x: x[1])

        new_link = None

        def add_link():
            link_id = (new_link['properties']['from'], new_link['properties']['to'])
            if link_id in links:
                links[link_id]['properties']['lines'].extend(new_link['properties']['lines'])
                links[link_id]['properties']['lines'] = list({v['id']:v for v in links[link_id]['properties']['lines']}.values())
                return

            links[link_id] = new_link

        if len(list(filter(lambda x: x[7] is None, group))) > 1:
            print(f'{group_key} overslaan vanwege lege geodata...')
            continue


        for link in group:
            data = {
                "pattern":link[0],
                "point_order":link[1],
                "point_type":link[2],
                "line_id":link[3],
                "line_label":link[4],
                "stopplace":link[5],
                "routepoint_2":link[6],
                "location":link[7]
            }

            if data['location'] is None:
                if data['point_type'] == 'stoppoint':
                    new_link['properties']['to'] = data['stopplace']
                    add_link()
                    new_link = None
                continue

            data['location'] = list(map(float, data['location'].split(' ')))

            if data['point_type'] == 'timing_point':
                new_link['geometry']['coordinates'].extend(
                    [data['location'][x + x], data['location'][x + x + 1]] for x in range(int(len(data['location']) / 2))
                )
                continue

            if new_link is not None:
                new_link['properties']['to'] = data['stopplace']
                add_link()

            new_link = {
                "geometry": {
                    "coordinates": [[data['location'][x + x], data['location'][x + x + 1]] for x in range(int(len(data['location']) / 2))],
                    "type": "LineString"
                },
                "properties": {
                    "from": data['stopplace'],
                    "lines": [
                        {
                            "color": "000000",
                            "id": data['line_id'],
                            "label": data['line_label']
                        }
                    ],
                    "to": None
                },
                "type": "Feature"
            }

    result['features'].extend(list(links.values()))

    for stopplace in stopplaces:
        stopplace_data = {
            'id':stopplace[0], 'name':stopplace[1],
            'location':stopplace[2]
        }
        f = {
            "geometry": {
            "coordinates": list(map(float, stopplace_data['location'].split(' '))),
            "type": "Point"
            },
            "properties": {
            "id": stopplace_data['id'],
            "station_id": stopplace_data['id'],
            "station_label": stopplace_data['name']
            },
            "type": "Feature"
        }
        result['features'].append(f)

    open('./output/loom.json', 'wb').write(json.dumps(result))


loom()
