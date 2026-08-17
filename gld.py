import xml.etree.ElementTree as ET
import geopandas
import pygml
import orjson as json
import os
from zipfile import ZipFile
import gzip
import requests
from netex import Netex
import sys
import sqlite3
from fudgeo import GeoPackage
from epiap import Epiap
import pandas as pd
from netex_json.netex_json import NetexJSON
import shutil
from datetime import datetime, timedelta

last_printed_time_at = datetime.now()
def printTime():
    now = datetime.now()
    diff = str(round((now - last_printed_time_at).seconds / 60))
    return f'[{now.strftime('%H:%M')} uur | {diff} min]'

# Netex processing for the province of Gelderland

general_folder = './gld_input/netex_general'
data_folder = './gld_input/netex_data'
non_netex_folder = './gld_input/other'
output_folder = './output'

network_inclusions = [
    # "DOVA:TransportAdministrativeZone:SAN",
    # "NL:DOVA:TransportAdministrativeZone:SAN",
    "DOVA:TransportAdministrativeZone:VZ",
    "NL:DOVA:TransportAdministrativeZone:VZ",
    "DOVA:TransportAdministrativeZone:ACH-RIV",
    "NL:DOVA:TransportAdministrativeZone:ACH-RIV",
    "DOVA:TransportAdministrativeZone:RAIL-AEW",
    "NL:DOVA:TransportAdministrativeZone:RAIL-AEW",
    "DOVA:TransportAdministrativeZone:TW",
    "NL:DOVA:TransportAdministrativeZone:TW",
    "DOVA:TransportAdministrativeZone:IJV",
    "NL:DOVA:TransportAdministrativeZone:IJV",
    # "DOVA:TransportAdministrativeZone:RAIL-VD",
    # "NL:DOVA:TransportAdministrativeZone:RAIL-VD",
    # "NL:DOVA:TransportAdministrativeZone:RAIL-KZE",
    # "DOVA:TransportAdministrativeZone:RAIL-KZE",
    "DOVA:TransportAdministrativeZone:ANF",
    "NL:DOVA:TransportAdministrativeZone:ANF"
]

if not os.path.exists(general_folder): quit()
if not os.path.exists(data_folder): quit()
if not os.path.exists(non_netex_folder): quit()

if os.path.exists(output_folder):
    shutil.rmtree(output_folder)

enum_contents = []
epiap_contents = []

for file in os.listdir(general_folder):
    is_epiap = file.upper().find('EPIAP') != -1
    split_path = os.path.splitext(file)

    if split_path[1] == '.gz':
        path = os.path.join(general_folder, file)
        
        split_path = os.path.splitext(path)
        print(f'{printTime()} Verwerken van {split_path[0]}')
        
        file = gzip.open(path, 'r')
        content = file.read()
        
        if is_epiap:
            epiap_contents.append(content)
        else:
            enum_contents.append(content)

if epiap_contents is not None:
    epiap_contents = list(map(lambda x: Epiap(None, x), epiap_contents))

linecode_categories = {}

if os.path.exists(f'{non_netex_folder}/abc-lijnen.xlsx'):
    print(f'{printTime()} Inladen ABC-categorieën')
    linecode_categories = pd.read_excel(f'{non_netex_folder}/abc-lijnen.xlsx', sheet_name='data').replace(float('nan'), None).astype({"code":"str"}).set_index('code')["ABC-Category"].to_dict()

for file in os.listdir(data_folder):
    split_path = os.path.splitext(file)

    if split_path[1] == '.gz':
        path = os.path.join(data_folder, file)
        
        split_path = os.path.splitext(path)
        print(f'{printTime()} Verwerken van {split_path[0]}')
        
        file = gzip.open(path, 'r')
        content = file.read()
        netex = Netex(str_content=content, epiap_list=epiap_contents, enum_list=enum_contents, options={
            "network_inclusions":network_inclusions, 
            "translate_to_dutch":True,
            'linecode_categories':linecode_categories
        })


gpkg = GeoPackage('./output/netex.gpkg')

if gpkg.is_schema_enabled is False:
    gpkg.enable_schema_extension()

aliasses = {
    'routes':{
        'id':'route_id',
        'line_id':'lijn_id',
        'mode_of_transport':'vervoersmiddel',
        "sub_mode_of_transport":'subcategorie vervoersmiddel',
        'line_number':'lijnnummer',
        'line_name':'lijnnaam',
        'line_code':'lijncode',
        'direction':'richting',
        'formula':'merknaam',
        'type_of_product':'producttype',
        'authority':'ov-autoriteit',
        'authority_code':'ov-autoriteit_code',
        'operator':'vervoerder',
        'operator_code':'vervoerder_code',
        'network':'concessie',
        'network_id':'concessie_id',
        'network_code':'concessie_code',
        'custom_category':'abc-categorie',
        'type_of_service':'soort ov-dienst'
    },
    'scheduled_stop_points':{
        # "id":stop_point.attrib['id'],
        "quay":'haltecode',
        "name":'perronnaam',
        "line_numbers":'lijnnummers',
        "lines":'lijnnamen',
        "modes_of_transport":'vervoersmiddel',
        "sub_modes_of_transport":'subcategorie vervoersmiddel',
        "line_codes":'lijncodes',
        "formulas":'merknamen',
        "types_of_product":'producttypes',
        "operators":'vervoerders',
        "networks":'concessies',
        'stopplace':'haltegroepcode',
        "stopplace_name":'haltegroepnaam',
        "stopplace_public_name":'haltegroepnaam_publiek',
        "stopplace_code_carrier":'haltegroepcode_vervoerder',
        "place":'plaatsnaam'
    }

}

for table in aliasses:
    for column in aliasses[table]:
        gpkg.schema.add_column_definition(
            table_name=table, column_name=column, name=aliasses[table][column]
        )

# Generate JSON
print(f'{printTime()} Genereren van JSON...')
netex_json = NetexJSON(language='nl')

print(f'{printTime()} Lijninformatie aanmaken...')
json_lines = netex_json.line_information()

print(f'{printTime()} JSON-bestand per lijn maken...')
netex_json.to_json(lines=json_lines)

region_data = dict(map(
    lambda x: (str(x[0]), x[1]),
    pd.read_excel(f'{non_netex_folder}/Regio_Lookup.xlsx').to_records(index=None)
))

print(f'{printTime()} Lijnen opdelen in regio\'s en concessies...')

json_lines_per_network = netex_json.divide_lines_by_network(json_lines)
json_lines_per_region = netex_json.divided_lines_per_region(json_lines_per_network, region_data)

open(f'{output_folder}/lines.json', 'wb').write(json.dumps(json_lines_per_region))
# netexJSON = NetexJSON()