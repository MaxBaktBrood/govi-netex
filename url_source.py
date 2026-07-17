

import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
from io import BytesIO
from netex import Netex

def getNetexViaURL(url:str, whitelist=None):
    netex_request = requests.get(
        url
    )

    if not netex_request.ok:
        raise Exception(f'Netex request geweigerd: {netex_request.status_code}')
    
    netex_zip = ZipFile(BytesIO(netex_request.content))
    for index, name in enumerate(netex_zip.namelist()):
        print(f'ZIP: Bestand {index}/{len(netex_zip.namelist())}: {name}')
        if os.path.splitext(name)[1] == '.xml':
            if whitelist and not any(x in name for x in whitelist):
                continue
            file = netex_zip.open(name, 'r')
            content = file.read()
            netex = Netex(str_content=content)
