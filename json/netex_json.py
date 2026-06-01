import typing
import geopandas as gpd
import json

class NetexJSON:

    def line_information(self):
        if not 'routes' in self.tables: return
        routes = self.tables['routes']

        processed = {}

        for line_id in routes['line_id'].unique():

            line_routes = routes[routes['line_id']==line_id]

            line = {
                "code": line_routes['line_code'].iloc[0],
                "line_name": line_routes['line_name'].iloc[0],
                "line_number": line_routes['line_number'].iloc[0],
                "line_mode_of_transport": line_routes['mode_of_transport'].iloc[0],
                "type": None,
                "routes": None,
                "notices": {}
            }

            line_type = line_routes['type_of_product'].iloc[0]
            if line_type is None:
                line_type = line_routes['formula'].iloc[0]
            
            line['type'] = line_type
            line['routes'] = json.loads(line_routes[['id', 'direction']].to_json())['features']

            processed.setdefault(line_id, line)

        return processed



    def __init__(self, netex_tables:dict[str, gpd.GeoDataFrame]):
        self.tables = netex_tables



