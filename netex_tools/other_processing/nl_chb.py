from lxml import etree as ET
import pygml
from typing import Optional
from datetime import datetime
import isodate
import sqlite3
import psycopg2
from netex_processing.nl import NetexBase
from netex_processing.dataclasses import Stopplace, Quay


class CHB(NetexBase):
    def process_chb(self, str_content = None, file = None):

        parser = ET.XMLParser(ns_clean=True)

        root: ET.Element = None
            
        if file is not None:
            tree = ET.parse(file, parser)
            root = tree.getroot()
        else:
            tree = ET.fromstring(str_content, parser)
            root = tree

        ns = {
            'c':'http://bison.connekt.nl/tmi8/chb/msg',
        }

        stopplaces = {}
        quays = {}

        for stopplace in root.findall('./c:stopplaces/c:stopplace', ns):

            available = False

            available_el = stopplace.find('./c:stopplacestatusdata/c:stopplacestatus', ns)
            if available_el is not None:
                available = (available_el.text == 'available')

            stopplace_id = None

            id_el = stopplace.find('./c:stopplacecode', ns)
            if id_el is not None:
                stopplace_id = id_el.text

            if not available or not stopplace_id: continue

            stopplace_data = Stopplace(stopplace_id)

            town_el = stopplace.find('./c:stopplacename/c:town', ns)
            if town_el is not None:
                stopplace_data.town = town_el.text

            street_el = stopplace.find('./c:stopplacename/c:street', ns)
            if street_el is not None:
                stopplace_data.street = street_el.text

            name_el = stopplace.find('./c:stopplacename/c:publicname', ns)
            if name_el is not None:
                
                stopplace_data.public_name = name_el.text
                if stopplace_data.town:
                    stopplace_data.name = f'{stopplace_data.town}, {stopplace_data.public_name}'
                else: stopplace_data.name = stopplace_data.public_name
            
            stopplaces[stopplace_data.id] = stopplace_data

            for quay in stopplace.findall('./c:quays/c:quay', ns):
                available = False

                available_el = quay.find('./c:quaystatusdata/c:quaystatus', ns)
                if available_el is not None:
                    available = (available_el.text == 'available')

                quay_id = None

                id_el = quay.find('./c:quaycode', ns)
                if id_el is not None:
                    quay_id = id_el.text

                if not available or not stopplace_id: continue

                quay_data = Quay(quay_id)

                direction_el = quay.find('./c:quaybearing/c:compassdirection', ns)
                if direction_el is not None:
                    quay_data.direction = int(direction_el.text)

                part_el = quay.find('./c:quaynamedata/c:stopsidecode', ns)
                if part_el is not None:
                    quay_data.public_code = part_el.text

                quays[quay_data.id] = quay_data
        print(len(stopplaces))
        print(len(quays))
        self.to_db('stopplaces', Stopplace, stopplaces, overwriteExisting=False)
        self.to_db('quays', Quay, quays, overwriteExisting=False)


