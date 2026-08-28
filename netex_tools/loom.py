import sqlite3
import orjson as json
from typing import Optional
import sys
from shapely.wkt import loads
import shapely
from shapely.geometry import *
import random

loom_line_colors = {}
def loom_line_color(id):
    if id in loom_line_colors: return loom_line_colors[id]
    r = lambda: random.randint(0, 255)
    loom_line_colors[id] = '#%02X%02X%02X' % (r(), r(), r())
    return loom_line_colors[id]

def cut_piece(line, distance):
    def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
        if distance <= 0.0 or distance >= line.length:
            return [LineString(line)]
        coords = list(line.coords)
        for i, p in enumerate(coords):
            pd = line.project(Point(p))
            if pd == distance:
                return [
                    LineString(coords[:i+1]),
                    LineString(coords[i:])]
            if pd > distance:
                cp = line.interpolate(distance)
                return [
                    LineString(coords[:i] + [(cp.x, cp.y)]),
                    LineString([(cp.x, cp.y)] + coords[i:])]

    cutoff_percentage = 250 / distance
    if distance < 500:
        cutoff_percentage = 0.25

    cutoff_from = line.length * cutoff_percentage
    cutoff_to = line.length - cutoff_from

    precut = cut(line,cutoff_from)
    if not precut: return line
    result = cut(precut[1], cutoff_to)
    if not result: return line
    return result[0]


db_path = './output/netex.db'

def loom(line_ids:list=[]):
    con = sqlite3.connect(db_path)
    
    cur = con.cursor()

    line_filter = ""
    if len(line_ids) > 0:
        line_filter = f"WHERE {
            " OR ".join(list(map(lambda x: f'lines.id = "{x}"', line_ids)))
        }"


    stopplaces_query = cur.execute("""
SELECT stopplaces.* from stopplaces
    """)

    stopplaces = stopplaces_query.fetchall()

    lines_query = cur.execute(
        f"""
SELECT pip.pattern, pip.point_order, CASE WHEN stoppoint IS NOT NULL THEN 'stoppoint' WHEN timing_point IS NOT NULL THEN 'timing_point' ELSE NULL END AS "point",
pip.line_id, pip.line_label, stopplace ,CONCAT(tp_routepoint, ssp_routepoint) as "routepoint_2", routelinks.location, pip.distance FROM (
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
LEFT JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.id = scheduled_stop_points.id
LEFT JOIN rel_quay_stopplace ON rel_quay_stopplace.quay = rel_stoppoint_quaycode.quay
WHERE scheduled_stop_points.id = pip.stoppoint
) stopplace,
(
SELECT timing_links.distance FROM timing_links
WHERE timing_links.id = pip.timing_link
) distance
FROM points_in_pattern pip
LEFT JOIN patterns ON patterns.id = pip.pattern
LEFT JOIN routes ON routes.id = patterns.route
LEFT JOIN lines ON lines.id = routes.line
{line_filter}
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
            if new_link['properties']['distance']:
                new_link['geometry'] = mapping(cut_piece(shape(new_link), new_link['properties']['distance']))
                new_link['geometry']['coordinates'] = list(new_link['geometry']['coordinates'])

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
                "location":link[7],
                "distance":link[8]
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
                    [data['location'][x + x + 1], data['location'][x + x]] for x in range(int(len(data['location']) / 2))
                )
                if new_link['properties']['distance'] and data['distance']: 
                    new_link['properties']['distance'] += data['distance']
                continue

            if new_link is not None:
                new_link['properties']['to'] = data['stopplace']
                add_link()

            new_link = {
                "geometry": {
                    "coordinates": [[data['location'][x + x + 1], data['location'][x + x]] for x in range(int(len(data['location']) / 2))],
                    "type": "LineString"
                },
                "properties": {
                    "from": data['stopplace'],
                    "lines": [
                        {
                            "color": loom_line_color(data['line_id']),
                            "id": data['line_id'],
                            "label": data['line_label']
                        }
                    ],
                    "to": None,
                    "distance":data['distance']
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
            "coordinates": list(map(float, reversed(stopplace_data['location'].split(' ')))),
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

if __name__ == "__main__":

    if len(sys.argv) > 1:
        loom(sys.argv[1:])
    else:
        loom()