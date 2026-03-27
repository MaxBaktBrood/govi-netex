import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
from netex import Netex
from si_source import getNetexSI

input_folder = './input'

if not os.path.isdir(input_folder):
    print('Map gemaakt om bestanden in te zetten: input')
    os.mkdir(input_folder)

secrets_file = {}
if os.path.exists('./secrets.json'):
    secrets_file = json.loads(
        open('secrets.json', 'r').read()
    )

print(f'Verwerken van Sloveense NeTEx')
for link, content in getNetexSI():
    print(f'Verwerken van {link}...')
    Netex(str_content=content)

for item in os.listdir(input_folder):
    path = os.path.join(input_folder, item)
    
    split_path = os.path.splitext(path)
    print(f'Verwerken van {split_path[0]}')

    if split_path[1] == '.zip':
        netex_zip = ZipFile(path)
        for index, name in enumerate(netex_zip.namelist()):
            print(f'ZIP: Bestand {index}/{len(netex_zip.namelist())}: {name}')
            if os.path.splitext(name)[1] == '.xml':
                file = netex_zip.open(name, 'r')
                content = file.read()
                netex = Netex(str_content=content)


    if split_path[1] == '.gz':
        file = gzip.open(path, 'r')
        content = file.read()
        netex = Netex(str_content=content)


# netex = Netex(file="NeTEx_ARR_NL_20260321_20260322_1405.xml")