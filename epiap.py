import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
import typing

class Epiap:

    stopplaces_per_quay = {}
    
    def __init__(self, file = None, str_content = None):
        print('Verwerken van EPIAP...')

        if file is None and str_content is None:
            raise Exception('File or string required')
        
        if file is not None:
            tree = ET.parse(file)
            self.root = tree.getroot()
        else:
            tree = ET.fromstring(str_content)
            self.root = tree
    
        self.ns = {
            'n':'http://www.netex.org.uk/netex',
            'gml':"http://www.opengis.net/gml/3.2"
        }

        compositeFrames = self.root.findall('./n:dataObjects/n:CompositeFrame', self.ns)

        if compositeFrames is None: return

        for compositeFrame in compositeFrames:
            stopplaces = compositeFrame.findall('./n:frames/n:SiteFrame/n:stopPlaces/n:StopPlace', self.ns)

            for stopplace in stopplaces:
                stopplace_code = None

                stopplace_code_el = stopplace.find('./n:privateCodes/n:PrivateCode[@type="StopPlaceCode"]', self.ns)

                if stopplace_code_el is not None: 
                    stopplace_code = stopplace_code_el.text
                else: continue

                quays = stopplace.findall('./n:quays/n:Quay', self.ns)

                for quay in quays:
                    quay_code = None

                    quay_code_el = quay.find('./n:privateCodes/n:PrivateCode[@type="QuayCode"]', self.ns)

                    if quay_code_el is not None: 
                        quay_code = quay_code_el.text
                        self.stopplaces_per_quay[quay_code] = stopplace_code

        return
