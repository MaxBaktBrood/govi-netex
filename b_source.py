import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile, is_zipfile
from io import BytesIO
import gzip
import requests

def getNetexB(secrets_file={}):
    if 'B_api_key' not in secrets_file: return []

    b_links = [
        "https://api.delijn.be/netex/v1/file",
    ]

    b_contents = []

    for link in b_links:
        print(f'Downloaden van {link}...')
        netex_request = requests.get(link, headers={
            'Ocp-Apim-Subscription-Key':secrets_file['B_api_key']
        })

        if not netex_request.ok:
            raise Exception(f'Netex request geweigerd: {netex_request.status_code}')

        netex_bytes = BytesIO(netex_request.content)

        if is_zipfile(netex_bytes):
            open('dump.zip', 'wb').write(netex_request.content)
            netex_zip = ZipFile(BytesIO(netex_request.content))
            for index, name in enumerate(netex_zip.namelist()):
                print(f'ZIP: Bestand {index}/{len(netex_zip.namelist())}: {name}')
                if os.path.splitext(name)[1] == '.xml':
                    file = netex_zip.open(name, 'r')
                    content = file.read()
                    print(type(content))
                    b_contents.append((link, content.decode('iso-8859-1')))
        else:
            b_contents.append((link, netex_request.content))

    return b_contents

