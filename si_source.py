import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile, is_zipfile
from io import BytesIO
import gzip
import requests

def getNetexSI(secrets_file={}):
    if 'SI_username' not in secrets_file: return None
    if 'SI_password' not in secrets_file: return None

    acces_token_request = requests.post("https://b2b.nap.si/uc/user/token", data={
        'grant_type':'password',
        'username':secrets_file['SI_username'],
        'password':secrets_file['SI_password']
    })

    if not acces_token_request.ok:
        raise Exception('Acces token request geweigerd.')

    acces_token = json.loads(acces_token_request.text)

    si_links = [
        "https://b2b.nap.si/data/b2b.netex.lines",
        # "https://b2b.ncup.si/data/b2b.netex.fares",
        # "https://b2b.nap.si/data/b2b.netex.operators",
        # "https://b2b.nap.si/data/b2b.netex.stopplaces",
        "https://b2b.nap.si/data/b2b.netex.bohinj",
        "https://b2b.nap.si/data/b2b.netex.brezice",
        "https://b2b.nap.si/data/b2b.netex.jesenice",
        "https://b2b.nap.si/data/b2b.netex.kranjska-gora",
        "https://b2b.nap.si/data/b2b.netex.nova-gorica"
    ]

    si_contents = []

    for link in si_links:
        print(f'Downloaden van {link}...')
        netex_request = requests.get(link, headers={
            'Host':'b2b.nap.si',
            'Authorization':f'Bearer {acces_token['access_token']}'
        })

        if not netex_request.ok:
            raise Exception(f'Netex request geweigerd: {netex_request.status_code}')

        netex_bytes = BytesIO(netex_request.content)

        if is_zipfile(netex_bytes):
            netex_zip = ZipFile(BytesIO(netex_request.content))
            for index, name in enumerate(netex_zip.namelist()):
                print(f'ZIP: Bestand {index}/{len(netex_zip.namelist())}: {name}')
                if os.path.splitext(name)[1] == '.xml':
                    file = netex_zip.open(name, 'r')
                    content = file.read()
                    si_contents.append((link, netex_bytes))
                else:
                    si_contents.append((link, netex_bytes))

    return si_contents
