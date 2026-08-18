import sqlite3
import geopandas


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

    lines_query = cur.execute(
    """
SELECT 
points_in_pattern.id, points_in_pattern.point_order, 
points_in_pattern.stoppoint as "stoppoint",
--COALESCE(points_in_pattern.stoppoint, LAST_VALUE(points_in_pattern.stoppoint) OVER (ORDER BY points_in_pattern.id AND points_in_pattern.point_order))  as "pattern_stoppoint",
points_in_pattern.timing_point as "timing_point",
lines.id AS "line_id", lines.number AS "line_label", rel_stoppoint_quaycode.quay AS "quay",
CONCAT(rel_timing_route_points.routepoint, scheduled_stop_points.route_point) AS "routepoint_2", 
routelinks.location FROM points_in_pattern

LEFT JOIN patterns ON patterns.id = points_in_pattern.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN lines ON lines.id = routes.line
LEFT JOIN rel_timing_route_points ON rel_timing_route_points.id = points_in_pattern.timing_point
LEFT JOIN scheduled_stop_points ON scheduled_stop_points.id = points_in_pattern.stoppoint
LEFT JOIN rel_point_route ON rel_point_route.route = routes.id AND rel_point_route.point = routepoint_2
LEFT JOIN routelinks ON routelinks.id = rel_point_route.link
LEFT JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.stoppoint = scheduled_stop_points.id
ORDER BY points_in_pattern.id AND points_in_pattern.point_order
    """)

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

    for group in grouped_links:
        group = sorted(group, key=lambda x: x[1])
        for link in group:
            data = {
                "id":link[0],
                "point_order":link[1],
                "stoppoint":link[2],
                "timing_point":link[3],
                "line_id":link[4],
                "line_label":link[5],
                "quay":link[6],
                "routepoint_2":link[7],
                "location":link[8]
            }
            if data['location'] is None:
                continue

            data['location'] = data['location'].split(' ')

            if data['timing_point'] is not None:
                result['features'][len(result['features'] - 1)]['geometry']['coordinates'].extend(
                    [coords[x + x], coords[x + x + 1]] for x in range(int(len(coords) / 2))
                )


            json = {
                "geometry": {
                    "coordinates": [],
                    "type": "LineString"
                },
                "properties": {
                    "from": None,
                    "lines": [
                    {
                        "color": "cd9c72",
                        "id": "0x130e070",
                        "label": "U1"
                    },
                    {
                        "color": "69bd51",
                        "id": "0x130e270",
                        "label": "U14"
                    }
                    ],
                    "to": "0x232df30"
                },
                "type": "Feature"
            },


lines_geodata()