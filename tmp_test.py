from netex_json.netex_json import NetexJSON
import pandas as pd
import orjson as json



netex_json = NetexJSON(language='nl')

json_lines = netex_json.line_information()

region_data = dict(map(
    lambda x: (str(x[0]), x[1]),
    pd.read_excel(f'./gld_input/other/Regio_Lookup.xlsx').to_records(index=None)
))

json_lines_per_network = netex_json.divide_lines_by_network(json_lines)
json_lines_per_region = netex_json.divided_lines_per_region(json_lines_per_network, region_data)

open(f'./output/lines.json', 'wb').write(json.dumps(json_lines_per_region))

netex_json.to_json(lines=json_lines)


