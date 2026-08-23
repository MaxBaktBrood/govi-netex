from lxml import etree as ET
import pygml
import typing
from datetime import datetime
import isodate
import sqlite3
from netex_processing.nl import NetexNL
from dataclasses import dataclass, fields, astuple, asdict
from netex_processing.dataclasses import Branding, ProductType, Operator, Authority, Area, RelResponsibilityArea, Line, Route, RelPointRoute, Routepoint, Routelink, Runtime, Waittime, TimingLink, RelTimingRoutePoint, Pattern, PointInPattern, ScheduledStopPoint, StopArea, AvailabilityCondition, Journey, AvailabilityPerJourney, RelStoppointQuaycode, RelQuayStopplace, Stopplace, Notice


class NetexEPIP(NetexNL):

    def get_stopplaces(self, site:ET.Element):
        rel_quay_stopplace: list[rel_quay_stopplace] = []
        stopplaces: dict[str, Stopplace] = {}

        for stopplace_el in site.findall(f"./n:stopPlaces/n:StopPlace", self.ns):
            code_el = stopplace_el.find("./n:keyList/n:KeyValue[n:Key='GlobalID']", self.ns)
            if code_el is None: continue
            code_value_el = code_el.find('./n:Value', self.ns)
            if code_value_el is None: continue
            
            rel_quay_stopplace.append(RelQuayStopplace(code_value_el.text, code_value_el.text))

            stopplace_data = Stopplace(stopplace_el.attrib['id'])

            location_el_lat = stopplace_el.find('./n:Centroid/n:Location/n:Latitude', self.ns)
            location_el_lng = stopplace_el.find('./n:Centroid/n:Location/n:Longitude', self.ns)
            if location_el_lng is not None and location_el_lat is not None:
                stopplace_data.location = ' '.join([location_el_lat.text, location_el_lng.text])

            if stopplace_data.location is not None and self.transformer is not None:
                stopplace_data.location = ' '.join(
                    map(str, self.transformer.transform(*stopplace_data.location.split(' ')))
                )

            name_el = stopplace_el.find('./n:Name', self.ns)
            if name_el is not None: stopplace_data.name = name_el.text

            stopplaces[stopplace_data.id] = stopplace_data

        self.to_db('rel_quay_stopplace', RelQuayStopplace, dict(
            (str(i), x) for i, x in enumerate(rel_quay_stopplace)
        ))
        self.to_db('stopplaces', Stopplace, stopplaces)
