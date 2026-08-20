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
                    [coords[x + x + 1], coords[x + x]] for x in range(int(len(coords) / 2))
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

if __name__ == '__main__':
    lines_geodata()