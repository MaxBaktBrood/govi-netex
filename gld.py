import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
from netex import Netex
import sys
import sqlite3
from fudgeo import GeoPackage
from epiap import Epiap

# Netex processing for the province of Gelderland

general_folder = './gld_input/netex_general'
data_folder = './gld_input/netex_data'
non_netex_folder = './gld_input/other'

network_inclusions = [
    "DOVA:TransportAdministrativeZone:SAN",
    "NL:DOVA:TransportAdministrativeZone:SAN",
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
    "DOVA:TransportAdministrativeZone:RAIL-VD",
    "NL:DOVA:TransportAdministrativeZone:RAIL-VD",
    "NL:DOVA:TransportAdministrativeZone:RAIL-KZE",
    "DOVA:TransportAdministrativeZone:RAIL-KZE",
    "DOVA:TransportAdministrativeZone:ANF",
    "NL:DOVA:TransportAdministrativeZone:ANF"
]

if not os.path.exists(general_folder): quit()
if not os.path.exists(data_folder): quit()
if not os.path.exists(non_netex_folder): quit()

enum_contents = []
epiap_contents = []

for file in os.listdir(general_folder):
    is_epiap = file.upper().find('EPIAP') != -1
    split_path = os.path.splitext(file)

    if split_path[1] == '.gz':
        path = os.path.join(general_folder, file)
        
        split_path = os.path.splitext(path)
        print(f'Verwerken van {split_path[0]}')
        
        file = gzip.open(path, 'r')
        content = file.read()
        
        if is_epiap:
            epiap_contents.append(content)
        else:
            enum_contents.append(content)

if epiap_contents is not None:
    epiap_contents = list(map(lambda x: Epiap(None, x), epiap_contents))

for file in os.listdir(data_folder):
    split_path = os.path.splitext(file)

    if split_path[1] == '.gz':
        path = os.path.join(data_folder, file)
        
        split_path = os.path.splitext(path)
        print(f'Verwerken van {split_path[0]}')
        
        file = gzip.open(path, 'r')
        content = file.read()
        netex = Netex(str_content=content, epiap_list=epiap_contents, enum_list=enum_contents, options={"network_inclusions":network_inclusions, "translate_to_dutch":True})


gpkg = GeoPackage('./output/netex.gpkg')

if gpkg.is_schema_enabled is False:
    gpkg.enable_schema_extension()

aliasses = {
    'routes':{
        'id':'route_id',
        'line_id':'lijn_id',
        'mode_of_transport':'vervoersmiddel',
        'line_number':'lijnnummer',
        'line_name':'lijnnaam',
        'line_code':'lijncode',
        'direction':'richting',
        'formula':'merknaam',
        'authority':'ov-autoriteit',
        'authority_code':'ov-autoriteit_code',
        'operator':'vervoerder',
        'operator_code':'vervoerder_code',
        'network':'concessie',
        'network_id':'concessie_id',
        'network_code':'concessie_code',
    },
    'scheduled_stop_points':{
        # "id":stop_point.attrib['id'],
        "quay":'haltecode',
        "name":'perronnaam',
        "line_numbers":'lijnnummers',
        "lines":'lijnnamen',
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