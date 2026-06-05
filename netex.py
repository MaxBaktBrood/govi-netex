import xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
import typing
from epiap import Epiap
from datetime import timedelta, datetime
import copy
import isodate
import sqlite3
import random

output_folder = './output'

class Netex:
    def line_information(self, line: ET.Element, resource:ET.Element, route_data={}, enum_list:list[ET.Element]| None=None) -> dict:
        route_data['line_id'] = line.attrib['id']

        mode_of_transport_el = line.find('./n:TransportMode', self.ns)
        if mode_of_transport_el is not None:
            route_data['mode_of_transport'] = mode_of_transport_el.text
            if 'translate_to_dutch' in self.options and self.options['translate_to_dutch'] is True:
                match route_data['mode_of_transport']:
                    case 'bus': route_data['mode_of_transport'] = 'bus'
                    case 'rail': route_data['mode_of_transport'] = 'trein'
                    case 'tram': route_data['mode_of_transport'] = 'tram'
                    case 'metro': route_data['mode_of_transport'] = 'metro'
                    case 'water': route_data['mode_of_transport'] = 'water'
        
        sub_modes_of_transport = line.findall('./n:TransportSubmode/*', self.ns)
        if len(sub_modes_of_transport) > 0:
            route_data['sub_mode_of_transport'] = ", ".join(
                map(
                    lambda x: x.text,
                    sub_modes_of_transport
                )
            )
            if 'translate_to_dutch' in self.options:
                dutch_modes = []
                for mode_el in sub_modes_of_transport:
                    match mode_el.text:
                        case 'localBus': dutch_modes.append('Buurtbus')
                        case 'regionalBus': dutch_modes.append('Streekbus')
                        case 'expressBus': dutch_modes.append('Snelbus')
                        case 'nightBus': dutch_modes.append('Nachtbus')
                        case 'mobilityBus': dutch_modes.append('Rolstoelbus')
                        case 'shuttleBus': dutch_modes.append('Pendelbus')
                        case 'highFrequencyBus': dutch_modes.append('Hoge frequentie')
                        case 'schoolBus': dutch_modes.append('Scholierenlijn')
                        case 'schoolAndPublicServiceBus': dutch_modes.append('Scholierenlijn')
                        case 'railReplacementBus': dutch_modes.append('Bus in plaats van trein')
                        case 'demandAndResponseBus': dutch_modes.append('Reserveerbus')
                        case 'unknown': dutch_modes.append('Onbekend')
                        case 'undefined': dutch_modes.append('Niet gespecificeerd')
                        case 'local': dutch_modes.append('Stoptrein')
                        case 'highSpeedRail': dutch_modes.append('Hogesnelheidstrein')
                        # case 'suburbanRailway': dutch_modes.append('')
                        case 'regionalRail': dutch_modes.append('Sneltrein')
                        case 'longDistance': dutch_modes.append('Intercity')
                        case 'international': dutch_modes.append('Internationale trein')
                        case 'specialTrain': dutch_modes.append('Speciale trein')
                        case 'metro': dutch_modes.append('Metro')
                        # case 'urbanRailway': dutch_modes.append('')
                        # case 'cityTram': dutch_modes.append('')
                        # case 'localTram': dutch_modes.append('')
                        case 'regionalTram': dutch_modes.append('Sneltram')
                        # case 'trainTram': dutch_modes.append('')
                        # case 'localCarFerry': dutch_modes.append('')
                        case 'localPassengerFerry': dutch_modes.append('Watertaxi')
                        case 'riverBus': dutch_modes.append('Waterbus')
                route_data['sub_mode_of_transport'] = ", ".join(dutch_modes)            

        line_number_el = line.find('./n:PublicCode', self.ns)
        if line_number_el is not None:
            route_data['line_number'] = line_number_el.text
        
        line_name_el = line.find('./n:Name', self.ns)
        if line_name_el is not None:
            route_data['line_name'] = line_name_el.text
        
        line_code_el = line.find('.//n:PrivateCode[@type="LinePlanningNumber"]', self.ns)
        if line_code_el is not None:
            route_data['line_code'] = line_code_el.text

        if route_data['line_code'] and 'linecode_categories' in self.options:
            if str(route_data['line_code']) in self.options['linecode_categories']:
                route_data['custom_category'] = self.options['linecode_categories'][str(route_data['line_code'])]
            else: route_data['custom_category'] = None

        branding_ref_el = line.find('./n:BrandingRef', self.ns)
        if branding_ref_el is not None and resource is not None:
            branding_ref = branding_ref_el.attrib['ref']
            branding_el = resource.find(f"./n:typesOfValue/n:Branding[@id='{branding_ref}']", self.ns)
            if branding_el is not None:
                name = branding_el.find('./n:Name', self.ns)
                if name is not None:
                    route_data['formula'] = name.text

        product_type_ref_el = line.find('./n:TypeOfProductCategoryRef', self.ns)
        if product_type_ref_el is not None and resource is not None:
            product_type_ref = product_type_ref_el.attrib['ref']
            product_type_el = resource.find(f"./n:typesOfValue/n:TypeOfProductCategory[@id='{product_type_ref}']", self.ns)
            if product_type_el is not None:
                name = product_type_el.find('./n:Name', self.ns)
                if name is not None:
                    route_data['type_of_product'] = name.text

        authority_ref_el = line.find('./n:AuthorityRef', self.ns)
        if authority_ref_el is not None:
            authority_ref = authority_ref_el.attrib['ref']

            if enum_list is not None:
                for enum in enum_list:
                    compositeFrames = enum.findall('./n:dataObjects/n:CompositeFrame', self.ns)
                    for compositeFrame in compositeFrames:
                        authority_el = compositeFrame.find(f"./n:frames/n:GeneralFrame/n:members/n:Authority[@id='{authority_ref}']", self.ns)
                        if authority_el is not None:
                            name = authority_el.find('./n:Name', self.ns)
                            if name is not None:
                                route_data['authority'] = name.text
                            code = authority_el.find('./n:ShortName', self.ns)
                            if code is not None:
                                route_data['authority_code'] = code.text
            
            if resource is not None:
                authority_el = resource.find(f'./n:organisations/n:Authority[@id="{authority_ref}"]', self.ns)
                if authority_el is not None:
                    name = authority_el.find('./n:Name', self.ns)
                    if name is not None:
                        route_data['authority'] = name.text
                    code = authority_el.find('./n:ShortName', self.ns)
                    if code is not None:
                        route_data['authority_code'] = code.text

            if route_data['authority'] is None:
                route_data['authority'] = authority_ref

        operator_ref_el = line.find('./n:OperatorRef', self.ns)
        if operator_ref_el is None:
            operator_ref_el = line.find('./n:additionalOperators/n:OperatorRef', self.ns) 

        if operator_ref_el is not None and resource is not None:
            operator_ref = operator_ref_el.attrib['ref']
            operator_el = resource.find(f"./n:organisations/n:Operator[@id='{operator_ref}']", self.ns)
            if operator_el is not None:
                name_el = operator_el.find('./n:Name', self.ns)
                if name_el is not None: route_data['operator'] = name_el.text
                code_el = operator_el.find('./n:ShortName', self.ns)
                if code_el is not None: route_data['operator_code'] = code_el.text

        if 'operator' not in route_data or route_data['operator'] is None and 'datasource' in self.defaults:
            route_data['operator'] = self.defaults['datasource']

        if 'operator_code' not in route_data or route_data['operator_code'] is None and 'datasource_code' in self.defaults:
            route_data['operator_code'] = self.defaults['datasource_code']

        if 'responsibilitySetRef' in line.attrib:
            responsibility_el = resource.find(f"./n:responsibilitySets/n:ResponsibilitySet[@id='{line.attrib['responsibilitySetRef']}']/n:roles", self.ns)
            if responsibility_el is not None:
                for role in responsibility_el:
                    roletypes = role.find('./n:StakeholderRoleType', self.ns)
                    organisation = role.find('./n:StakeholderRoleType', self.ns)

                    if (roletypes is not None and 'EntityLegalOwnership' in roletypes.text.split(' ')) or roletypes is None:
                        area = role.find('./n:ResponsibleAreaRef', self.ns)

                        if area is not None and enum_list is not None:
                            for enum in enum_list:
                                compositeFrames = enum.findall('./n:dataObjects/n:CompositeFrame', self.ns)
                                for compositeFrame in compositeFrames:
                                    area_el = compositeFrame.find(f"./n:frames/n:GeneralFrame/n:members/n:TransportAdministrativeZone[@id='{area.attrib['ref']}']", self.ns)
                                    if area_el is not None:
                                        route_data['network_id'] = area_el.attrib['id']
                                        name = area_el.find('./n:Name', self.ns)
                                        if name is not None:
                                            route_data['network'] = name.text
                                        code = area_el.find('./n:ShortName', self.ns)
                                        if code is not None:
                                            route_data['network_code'] = code.text

                        if route_data['network'] is None:
                            route_data['network'] = area.attrib['ref']
                            route_data['network_id'] = area.attrib['ref']
        
        type_of_service_ref_el = line.find('./n:TypeOfServiceRef', self.ns)
        if type_of_service_ref_el is not None:
            type_of_service_ref = type_of_service_ref_el.attrib['ref']

            if enum_list is not None:
                for enum in enum_list:
                    compositeFrames = enum.findall('./n:dataObjects/n:CompositeFrame', self.ns)
                    for compositeFrame in compositeFrames:
                        type_of_service_el = compositeFrame.find(f"./n:frames/n:GeneralFrame/n:members/n:ValueSet/n:values/n:TypeOfService[@id='{type_of_service_ref}']", self.ns)
                        if type_of_service_el is not None:
                            name = type_of_service_el.find('./n:Name', self.ns)
                            if name is not None:
                                route_data['type_of_service'] = name.text


        return route_data


    def craftRoutes(self, service:ET.Element, resource:ET.Element | None=None, timetable:ET.Element | None=None, enum_list:list[ET.Element]| None=None, crs='wgs84'):
        routes = service.find('./n:routes', self.ns)

        # fallback 1: GERMANY
        if routes is None:
            for pattern in service.findall('./n:journeyPatterns/n:ServiceJourneyPattern[n:RouteView]', self.ns):
                line_geodata = {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": []
                    },
                    "properties":{}
                }
                points_geodata = {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiPoint",
                        "coordinates": []
                    },
                    "properties":{}
                }

                route_data = {
                    'id':None,
                    'line_id':None,
                    'mode_of_transport':None,
                    'sub_mode_of_transport':None,
                    'line_number':None,
                    'line_name':None,
                    'line_code':None,
                    'direction':None,
                    'formula':None,
                    'type_of_product':None,
                    'authority':None,
                    'authority_code':None,
                    'operator':None,
                    'operator_code':None,
                    'network':None,
                    'network_id':None,
                    'network_code':None,
                    'type_of_service':None
                }

                line_ref_el = pattern.find('./n:RouteView/n:LineRef', self.ns)
                line_ref = None
                if line_ref_el is not None: 
                    line_ref = line_ref_el.attrib['ref']
                    route_data['line_id'] = line_ref
                line = service.find(f"./n:lines/n:Line[@id='{line_ref}']", self.ns)

                previous_stoppoint = None

                for point in pattern.findall('./n:pointsInSequence/n:StopPointInJourneyPattern', self.ns):
                    stoppoint_ref = point.find('./n:ScheduledStopPointRef', self.ns).attrib['ref']
                    stoppoint = None
                    stoppoint_location = service.find(f"./n:scheduledStopPoints/n:ScheduledStopPoint[@id='{stoppoint_ref}']/n:Location", self.ns)

                    if stoppoint_location is not None:
                        gml = stoppoint_location.find("./gml:pos", self.ns)

                        if gml is not None:
                            stoppoint = list(pygml.basics.parse_pos(gml.text))
                        else:
                            lng = stoppoint_location.find('./n:Longitude', self.ns)
                            lat = stoppoint_location.find('./n:Latitude', self.ns)

                            if lng is not None and lat is not None:
                                stoppoint = [lng.text, lat.text]
                    
                    if stoppoint is not None:        
                        points_geodata['geometry']['coordinates'].append(stoppoint)

                        if previous_stoppoint is not None:
                            line_geodata['geometry']['coordinates'].append([
                                previous_stoppoint,
                                stoppoint
                            ])
                            previous_stoppoint = None

                    if stoppoint:
                        previous_stoppoint = stoppoint

                if line is not None:
                    route_data = self.line_information(line, resource, route_data, enum_list)

                if 'network_witelist' in self.options:
                    if route_data['network_id'] not in self.options['network_inclusions']:
                        continue
                
                if 'network_exclutions' in self.options:
                    if route_data['network_id'] in self.options['network_exclutions']:
                        continue
                
                self.notice_able_ids.append(route_data['line_id'])
                
                # For Germany useless here
                direction_el = pattern.find('./n:DirectionType', self.ns)
                if direction_el is not None:
                    route_data['direction'] = direction_el.text
                    
                line_geodata['properties'] = route_data
                points_geodata['properties'] = route_data

                line_gdf = gpd.GeoDataFrame.from_features(
                    features=[line_geodata]
                ).set_crs(crs).to_crs(self.defaults['crs'])

                line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

                points_gdf = gpd.GeoDataFrame.from_features(
                    features=[points_geodata]
                ).set_crs(crs).to_crs(self.defaults['crs'])

                points_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routepoints", driver="GPKG", mode="a")


        # fallback 2: AUSTRIA
        service_journeys = None
        if timetable is not None:
            service_journeys = timetable.find('./n:vehicleJourneys', self.ns)

        if routes is None and service_journeys is not None: 
            patterns = service.find('./n:journeyPatterns', self.ns)
            processed_routes = []

            for journey in service_journeys.findall('./n:ServiceJourney', self.ns):
                line_geodata = {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": []
                    },
                    "properties":{}
                }

                route_data = {
                    'id':None,
                    'line_id':None,
                    'mode_of_transport':None,
                    'sub_mode_of_transport':None,
                    'line_number':None,
                    'line_name':None,
                    'line_code':None,
                    'direction':None,
                    'formula':None,
                    'type_of_product':None,
                    'authority':None,
                    'authority_code':None,
                    'operator':None,
                    'operator_code':None,
                    'network':None,
                    'network_id':None,
                    'network_code':None,
                    'type_of_service':None
                }

                made_up_route_id = []

                line_ref_el = journey.find('./n:LineRef', self.ns)
                line_ref = None
                if line_ref_el is not None: 
                    line_ref = line_ref_el.attrib['ref']
                    made_up_route_id.append(line_ref)
                line = service.find(f"./n:lines/n:Line[@id='{line_ref}']", self.ns)

                journey_pattern_ref_el = journey.find('./n:ServiceJourneyPatternRef', self.ns)
                if journey_pattern_ref_el is not None:
                    made_up_route_id.append(journey_pattern_ref_el.attrib['ref'])
                    route_data['id'] = "___".join(made_up_route_id)

                    if route_data['id'] in processed_routes: continue
                    processed_routes.append(route_data['id'])

                    journey_pattern_ref = journey_pattern_ref_el.attrib['ref']
                    journey_pattern = service.find(f"./n:journeyPatterns/n:ServiceJourneyPattern[@id='{journey_pattern_ref}']", self.ns)
                    
                    if journey_pattern is not None:
                        for link in journey_pattern.findall('./n:linksInSequence/n:ServiceLinkInJourneyPattern', self.ns):
                            servicelink_ref_el = link.find('./n:ServiceLinkRef', self.ns)
                            servicelinks = service.find('./n:serviceLinks', self.ns)

                            if servicelink_ref_el is not None and servicelinks is not None:
                                ref = servicelink_ref_el.attrib['ref']
                                servicelink = servicelinks.find(f'./n:ServiceLink[@id="{ref}"]', self.ns)

                                line_string = servicelink.find(f'./gml:LineString', self.ns)
                                if line_string is not None:
                                    line_string_data = pygml.parse(ET.tostring(line_string))
                                    line_geodata['geometry']['coordinates'].append(dict(line_string_data.__geo_interface__)['coordinates'])

                        direction_el = journey_pattern.find('./n:DirectionType', self.ns)
                        if direction_el: route_data['direction'] = direction_el.text()
                
                if len(line_geodata['geometry']['coordinates']) == 0: continue

                if line is not None:
                    route_data = self.line_information(line, resource, route_data, enum_list)
                
                if 'network_inclusions' in self.options:
                    if route_data['network_id'] not in self.options['network_inclusions']:
                        continue
                
                if 'network_exclutions' in self.options:
                    if route_data['network_id'] in self.options['network_exclutions']:
                        continue

                self.notice_able_ids.append(route_data['line_id'])

                line_geodata['properties'] = route_data

                line_gdf = gpd.GeoDataFrame.from_features(
                    features=[line_geodata]
                ).set_crs(crs).to_crs(self.defaults['crs'])
                line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

            return

        if routes is None: 
            return print('Overgeslagen; geen routedata')

        # Original (NETHERLANDS)
        for route in routes:
            line_ref_el = route.find('./n:LineRef', self.ns)
            line_ref = None
            if line_ref_el is not None: line_ref = line_ref_el.attrib['ref']
            line = service.find(f"./n:lines/n:Line[@id='{line_ref}']", self.ns)

            if line_ref_el is None: print('Geen lijn')

            points = route.find('./n:pointsInSequence', self.ns)

            if points is None: continue

            route_data = {
                'id':route.attrib['id'],
                'line_id':None,
                'mode_of_transport':None,
                'sub_mode_of_transport':None,
                'line_number':None,
                'line_name':None,
                'line_code':None,
                'direction':None,
                'formula':None,
                'type_of_product':None,
                'authority':None,
                'authority_code':None,
                'operator':None,
                'operator_code':None,
                'network':None,
                'network_id':None,
                'network_code':None,
                'type_of_service':None
            }
            

            if line is not None:
                route_data = self.line_information(line, resource, route_data, enum_list)

            if 'network_inclusions' in self.options:
                if route_data['network_id'] not in self.options['network_inclusions']:
                    continue
            
            if 'network_exclutions' in self.options:
                if route_data['network_id'] in self.options['network_exclutions']:
                    continue
            
            self.notice_able_ids.append(route_data['line_id'])

            line_geodata = {
                "type": "Feature",
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": []
                },
                "properties":{}
            }
            points_geodata = {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPoint",
                    "coordinates": []
                },
                "properties":{}
            }

            previous_routepoint = None

            for point in points:
                routepoint_ref = point.find('./n:RoutePointRef', self.ns).attrib['ref']
                routepoint = None
                routepoint_location = service.find(f"./n:routePoints/n:RoutePoint[@id='{routepoint_ref}']/n:Location", self.ns)

                if routepoint_location is not None:
                    gml = routepoint_location.find("./gml:pos", self.ns)

                    if gml is not None:
                        routepoint = list(pygml.basics.parse_pos(gml.text))
                    else:
                        lng = routepoint_location.find('./n:Longitude', self.ns)
                        lat = routepoint_location.find('./n:Latitude', self.ns)

                        if lng is not None and lat is not None:
                            routepoint = [lng.text, lat.text]
                
                if routepoint is not None:        
                    points_geodata['geometry']['coordinates'].append(routepoint)

                    if previous_routepoint is not None:
                        line_geodata['geometry']['coordinates'].append([
                            previous_routepoint,
                            routepoint
                        ])
                        previous_routepoint = None
                
                routelink_el = point.find('./n:OnwardRouteLinkRef', self.ns)

                if routelink_el is None: 
                    if routepoint:
                        previous_routepoint = routepoint
                    continue
                
                routelink_ref = routelink_el.attrib['ref']
                routelink = pygml.parse(ET.tostring(service.find(f"./n:routeLinks/n:RouteLink[@id='{routelink_ref}']/gml:LineString", self.ns)))
                line_geodata['geometry']['coordinates'].append(dict(routelink.__geo_interface__)['coordinates'])
            
            if len(line_geodata['geometry']['coordinates']) == 0:
                journey_patterns = service.find('./n:journeyPatterns', self.ns)
                servicelinks = service.find('./n:serviceLinks', self.ns)

                if journey_patterns is not None and servicelinks is not None:
                    for route_ref in journey_patterns.findall(f'./n:ServiceJourneyPattern/RouteRef[@ref="{route.attrib['id']}"]', self.ns):
                        pattern: ET.Element = route_ref.find('..')

                        for link in pattern.findall('./n:linksInSequence/n:ServiceLinkInJourneyPattern', self.ns):
                            servicelink_ref_el = link.find('./n:ServiceLinkRef', self.ns)
                            if servicelink_ref_el is not None and servicelinks is not None:
                                ref = servicelink_ref_el.attrib['ref']
                                servicelink = servicelinks.find(f'./n:ServiceLink[@id="{ref}"]', self.ns)

                                line_string = servicelink.find(f'./gml:LineString', self.ns)
                                if line_string is not None:
                                    line_string_data = pygml.parse(ET.tostring(line_string))
                                    line_geodata['geometry']['coordinates'].append(dict(line_string_data.__geo_interface__)['coordinates'])
            
            direction_el = route.find('./n:DirectionType', self.ns)
            if direction_el is not None:
                route_data['direction'] = direction_el.text
                if 'translate_to_dutch' in self.options and self.options['translate_to_dutch'] is True:
                    match route_data['direction']:
                        case 'outbound': route_data['direction'] = 'uitgaand'
                        case 'inbound': route_data['direction'] = 'inkomend'
                
            line_geodata['properties'] = route_data
            points_geodata['properties'] = route_data

            line_gdf = gpd.GeoDataFrame.from_features(
                features=[line_geodata]
            ).set_crs(crs).to_crs(self.defaults['crs'])

            line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

            points_gdf = gpd.GeoDataFrame.from_features(
                features=[points_geodata]
            ).set_crs(crs).to_crs(self.defaults['crs'])

            points_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routepoints", driver="GPKG", mode="a")
        
        return

    # def getEpiapQuay(self, ref:str, epiap_list:list[ET.Element]=[]):
    #     for epiap in epiap_list:
    #         quay = epiap.find(f".//n:Quay[@id='{ref}']", self.ns)
    #         if quay is None:
    #           quay = epiap.find(f".//n:Quay[@id='{ref}']/n:privateCodes[n:PrivateCode='{ref}']", self.ns) 
    #           if quay is not None: quay = quay.find('..')
    #         if quay is not None:
    #             codeEl = quay.find('../../n:privateCodes/PrivateCode', self.ns)
    #             stopplaceCode = None
    #             if codeEl is not None: stopplaceCode = codeEl.text
    #             name = quay.find('../../n:Name', self.ns)

    #             gml = quay.find("./{gml}*", self.ns)
    #             if gml is None: gml = gml = quay.find("./n:Centroid/n:Location/gml:pos", self.ns)

    #             if gml is not None:
    #                 if gml.tag == 'gml:pos':
    #                     location = list(pygml.basics.parse_pos(gml.text))
    #                 else:
    #                     location = pygml.parse(gml)
    #             else:
    #                 lng = quay.find('./n:Location/n:Longitude', self.ns)
    #                 lat = quay.find('./n:Location/n:Latitude', self.ns)

    #                 if lng is not None and lat is not None:
    #                     location = [lng.text, lat.text]
    #     pass
    
    def craftJourneys(self, service:ET.Element, timetable:ET.Element, resource:ET.Element|None=None, enum_list:list[ET.Element]|None=None, epiap_list:list[Epiap]|None=None, crs='wgs84', loom=True, time_table = True):
        journeys = timetable.find('./n:vehicleJourneys', self.ns)
        patterns = service.find('./n:journeyPatterns', self.ns)
        time_demand_types = service.find('./n:timeDemandTypes', self.ns)
        timing_links = service.find('./n:timingLinks', self.ns)
        stop_points = service.find('./n:scheduledStopPoints', self.ns)
        timing_points = service.find('./n:TimingPoints', self.ns) #only for loom
        route_links = service.find(f"./n:routeLinks", self.ns) #only for loom
        stop_areas = service.find('./n:stopAreas', self.ns)
        availability_conditions = timetable.find('./n:contentValidityConditions', self.ns)

        def route_link_index(route_links: ET.Element):
                        summary = {}
                        for link in route_links.findall('./*', self.ns):
                            geodata = pygml.parse(ET.tostring(link.find(f"./gml:LineString", self.ns)))
                            link_from = link.find('./n:FromPointRef', self.ns).attrib['ref']
                            link_to = link.find('./n:ToPointRef', self.ns).attrib['ref']
                            summary[f'{link_from} - {link_to}'] = dict(geodata.__geo_interface__)['coordinates']
                        return summary
        loom_route_links = {}
        if loom and route_links: loom_route_links = route_link_index(route_links)
        print('links for loom: ' + str(len(loom_route_links)))

        def quay_stoppoint_assigner(el: ET.Element):
            stoppoint_el = el.find(f'./n:ScheduledStopPointRef', self.ns)
            stoppoint = None
            if stoppoint_el is not None and 'ref' in stoppoint_el.attrib: stoppoint = stoppoint_el.attrib['ref']
            quay_el = el.find(f'./n:QuayRef', self.ns)
            quay = None
            if quay_el is not None and 'ref' in quay_el.attrib: quay = quay_el.attrib['ref'].replace(
                'NL:CHB:quay:','NL:Q:'
            ).replace(
                'NL:CHB:Quay:','NL:Q:'
            )

            if stoppoint is None and quay is None: raise Exception()
            return (stoppoint, quay)

        quays_per_stoppoint = dict(map(
            quay_stoppoint_assigner, service.findall(f'./n:stopAssignments/n:PassengerStopAssignment', self.ns)
        ))

        stop_points_geodata = {
            "type": "FeatureCollection",
            "features": {}
        }

        loom_geodata = {}

        if journeys is None: return

        vehicle_types = None
        if resource:
            vehicle_types = resource.find('./n:vehicleTypes', self.ns)

        if journeys is None: return print('Geen ritdata')

        for journey in journeys:

            journey_data = {
                'id':journey.attrib['id'],
                'number': None,
                'route':None,
                'line_id':None,
                'in_scope_of_operator':None,
                'distance':0,
                'dru':None,
                'direction':None,
                'line_name':None,
                'line_number':None,
                'network':None,
                'network_id':None,
                'network_code':None,
                'realtime_info': None
            }

            journey_timestamps = [

            ]

            line_data = {
                'line_id':None,
                'mode_of_transport':None,
                'sub_mode_of_transport':None,
                'line_number':None,
                'line_name':None,
                'line_code':None,
                'direction':None,
                'formula':None,
                'type_of_product':None,
                'authority':None,
                'authority_code':None,
                'operator':None,
                'operator_code':None,
                'network':None,
                'network_code':None,
                'type_of_service':None,
            }

            time_demand_type = None
            time_demand_type_ref = journey.find('./n:TimeDemandTypeRef', self.ns)
            if time_demand_type_ref is not None and time_demand_types is not None:
                time_demand_type = time_demand_types.find(f'./n:TimeDemandType[@id="{time_demand_type_ref.attrib['ref']}"]', self.ns)

            pattern_ref = journey.find('./n:ServiceJourneyPatternRef', self.ns)
            if pattern_ref is not None and patterns is not None:
                pattern = patterns.find(f'./n:ServiceJourneyPattern[@id="{pattern_ref.attrib['ref']}"]', self.ns)
                if pattern is not None:
                    routeref_el = pattern.find('./n:RouteRef', self.ns)
                    if routeref_el is not None:
                        routeref = routeref_el.attrib['ref']
                        journey_data['route'] = routeref
                        line_ref_el = service.find(f'./n:routes/n:Route[@id="{routeref_el.attrib['ref']}"]/n:LineRef', self.ns)
                        if line_ref_el is not None and 'ref' in line_ref_el.attrib:
                            journey_data['line_id'] = line_ref_el.attrib['ref']
                            line = service.find(f'./n:lines/n:Line[@id="{journey_data['line_id']}"]', self.ns)
                            if line is not None:
                                if resource is not None:
                                    line_data = self.line_information(line, resource, line_data, enum_list)

                                line_name = None
                                line_number = None
                                
                                line_number_el = line.find('./n:PublicCode', self.ns)
                                if line_number_el is not None:
                                    line_number = line_number_el.text
                                    line_name = line_number_el.text
                                
                                line_name_el = line.find('./n:Name', self.ns)
                                if line_name_el is not None:
                                    if line_name:
                                        line_name += f" {line_name_el.text}"
                                    else: line_name = line_name_el.text

                                journey_data['line_name'] = line_name
                                journey_data['line_number'] = line_number
                            
                                if 'responsibilitySetRef' in line.attrib:
                                    responsibility_el = resource.find(f"./n:responsibilitySets/n:ResponsibilitySet[@id='{line.attrib['responsibilitySetRef']}']/n:roles", self.ns)
                                    if responsibility_el is not None:
                                        for role in responsibility_el:
                                            roletypes = role.find('./n:StakeholderRoleType', self.ns)
                                            organisation = role.find('./n:StakeholderRoleType', self.ns)

                                            if (roletypes is not None and 'EntityLegalOwnership' in roletypes.text.split(' ')) or roletypes is None:
                                                area = role.find('./n:ResponsibleAreaRef', self.ns)

                                                if area is not None and enum_list is not None:
                                                    for enum in enum_list:
                                                        compositeFrames = enum.findall('./n:dataObjects/n:CompositeFrame', self.ns)
                                                        for compositeFrame in compositeFrames:
                                                            area_el = compositeFrame.find(f"./n:frames/n:GeneralFrame/n:members/n:TransportAdministrativeZone[@id='{area.attrib['ref']}']", self.ns)
                                                            if area_el is not None:
                                                                journey_data['network_id'] = area_el.attrib['id']
                                                                name = area_el.find('./n:Name', self.ns)
                                                                if name is not None:
                                                                    journey_data['network'] = name.text
                                                                code = area_el.find('./n:ShortName', self.ns)
                                                                if code is not None:
                                                                    journey_data['network_code'] = code.text

                                                if journey_data['network'] is None:
                                                    journey_data['network'] = area.attrib['ref']
                                                    journey_data['network_id'] = area.attrib['ref']

                    if 'network_inclusions' in self.options:
                        if journey_data['network_id'] not in self.options['network_inclusions']:
                            continue
                    
                    if 'network_exclutions' in self.options:
                        if journey_data['network_id'] in self.options['network_exclutions']:
                            continue

                    direction_el = pattern.find('./n:DirectionType', self.ns)
                    if direction_el is not None:
                        direction = direction_el.text
                        journey_data['direction'] = direction

                    time_tracker = None
                    if journey.find('./n:DepartureTime', self.ns) is not None:
                        time_tracker = datetime.strptime(journey.find('./n:DepartureTime', self.ns).text, "%H:%M:%S")

                    time_in_service = {
                        'from':copy.deepcopy(time_tracker),
                        'to':None
                    }

                    loom_route_points = []
                    
                    points = pattern.findall('./n:pointsInSequence/*', self.ns)
                    for index, point in enumerate(points):

                        if point.tag == f'{{{self.ns['n']}}}TimingPointInJourneyPattern':
                            if not loom: continue
                            timingpoint_ref = point.find('./n:TimingPointRef', self.ns)
                            if timingpoint_ref is not None and timing_points is not None:  
                                timing_point: ET.Element = timing_points.find(f'./n:TimingPoint[@id="{stoppoint_ref.attrib['ref']}"]', self.ns)
                                if timing_point is not None:
                                        route_point_el = timing_point.find('./n:projections/n:PointProjection/n:ProjectToPointRef', self.ns)
                                        if route_point_el is not None and 'ref' in route_point_el.attrib:
                                            loom_route_points.append(route_point_el.attrib['ref'])
                            continue
                        
                        stoppoint_ref = point.find('./n:ScheduledStopPointRef', self.ns)
                        quay = None

                        if stoppoint_ref is not None and 'ref' in stoppoint_ref.attrib:
                            if stoppoint_ref.attrib['ref'] in quays_per_stoppoint:
                                quay = quays_per_stoppoint[stoppoint_ref.attrib['ref']]

                        driving_time = None
                        wait_time = None

                        timing_link_ref = point.find('./n:OnwardTimingLinkRef', self.ns)
                        if timing_link_ref is not None and timing_links is not None:
                            ref = timing_link_ref.attrib['ref']
                            timing_link = timing_links.find(f'./n:TimingLink[@id="{ref}"]', self.ns)
                            distance_el = timing_link.find('./n:Distance', self.ns)
                            if distance_el is not None:
                                distance = float(distance_el.text)
                                journey_data['distance'] += distance
                            
                            if time_demand_type is not None:
                                runtime_el = time_demand_type.find(f'./n:runTimes/n:JourneyRunTime/n:TimingLinkRef[@ref="{ref}"]/../n:RunTime', self.ns)
                                if runtime_el is not None:
                                    driving_time = isodate.parse_duration(runtime_el.text)
                                
                                waittime_el = time_demand_type.find(f'./n:waitTimes/n:JourneyWaitTime/n:ScheduledStopPointRef[@ref="{stoppoint_ref.attrib['ref']}"]/../n:WaitTime', self.ns)
                                if waittime_el is not None:
                                    wait_time = isodate.parse_duration(waittime_el.text)

                        # passenger_stop_assignment = service.find(f'./n:stopAssignments/n:PassengerStopAssignment/n:ScheduledStopPointRef[@ref="{stoppoint_ref.attrib['ref']}"]/..', self.ns)
                        # if passenger_stop_assignment is not None:
                        #     quay_el = passenger_stop_assignment.find('./n:QuayRef', self.ns)
                        #     if quay_el is not None and 'ref' in quay_el.attrib:
                        #         quay = quay_el.attrib['ref'].upper().replace('NL:CHB:QUAY:','NL:Q:')
                        #     else:
                        #         print('Geen quay voor ' + stoppoint_ref.attrib['ref'])
                        # else: print('Geen PSA voor ' + stoppoint_ref.attrib['ref'])
                        
                        
                        point_id = None
                        if quay: point_id = quay
                        else: point_id = stoppoint_ref.attrib['ref']

                        quay_properties = {
                            'quay_name':None,
                            'quay_code':quay,
                            'quay_location':None,

                        }

                        if stoppoint_ref is not None and stop_points is not None:  
                            stop_point: ET.Element = stop_points.find(f'./n:ScheduledStopPoint[@id="{stoppoint_ref.attrib['ref']}"]', self.ns)
                            if stop_point is not None:
                                if point_id not in stop_points_geodata['features']:
                                    point_geodata = {
                                        "type": "Feature",
                                        "geometry": {
                                            "type": "MultiPoint",
                                            "coordinates": []
                                        },
                                        "properties":{
                                            # "id":stop_point.attrib['id'],
                                            "quay":quay,
                                            "name":None,
                                            "line_numbers":set(),
                                            "lines":set(),
                                            "line_codes":set(),
                                            "formulas":set(),
                                            'types_of_product':set(),
                                            'modes_of_transport':set(),
                                            'sub_modes_of_transport':set(),
                                            "operators":set(),
                                            "networks":set(),
                                            "stopplace":None,
                                            "stopplace_name":None,
                                            "stopplace_public_name":None,
                                            "stopplace_code_carrier":None,
                                            "place":None
                                        }
                                    }

                                    stop_point_name = stop_point.find("./n:Name", self.ns)
                                    if stop_point_name is not None:
                                        point_geodata['properties']['name'] = stop_point_name.text
                                        quay_properties['quay_name'] = stop_point_name.text

                                    stop_area_ref_el = stop_point.find("./n:stopAreas/n:StopAreaRef", self.ns)
                                    if stop_area_ref_el is not None:
                                        ref = stop_area_ref_el.attrib['ref']
                                        stop_area = stop_areas.find(f'./n:StopArea[@id="{ref}"]', self.ns)
                                        if stop_area is not None:
                                            name_el = stop_area.find("./n:Name", self.ns)
                                            if name_el is not None: 
                                                point_geodata['properties']['stopplace_name'] = name_el.text

                                            public_name_el = stop_area.find("./n:Name", self.ns)
                                            if public_name_el is not None: 
                                                point_geodata['properties']['stopplace_public_name'] = public_name_el.text

                                            code_el = stop_area.find("./n:privateCodes/n:PrivateCode[@type='UserStopAreaCode']", self.ns)
                                            if code_el is not None: point_geodata['properties']['stopplace_code_carrier'] = code_el.text

                                            place_el = stop_area.find("./n:TopographicPlaceView/n:Name", self.ns)
                                            if place_el is not None: point_geodata['properties']['place'] = place_el.text

                                    if epiap_list:
                                        for epiap in epiap_list:
                                            if quay in epiap.stopplaces_per_quay:
                                                point_geodata['properties']['stopplace'] = epiap.stopplaces_per_quay[quay]

                                    stop_points_geodata['features'].setdefault(point_id, point_geodata)

                                stop_point_location = stop_point.find("./n:Location", self.ns)

                                if stop_point_location is not None:
                                    gml = stop_point_location.find("./gml:pos", self.ns)
                                    location = None

                                    if gml is not None:
                                        location = list(pygml.basics.parse_pos(gml.text))
                                    else:
                                        lng = stop_point_location.find('./n:Longitude', self.ns)
                                        lat = stop_point_location.find('./n:Latitude', self.ns)

                                        if lng is not None and lat is not None:
                                            location = [lng.text, lat.text]

                                    quay_properties['quay_location'] = ','.join(map(lambda x: str(x), location))

                                    if location not in stop_points_geodata['features'][point_id]['geometry']['coordinates']:
                                        stop_points_geodata['features'][point_id]['geometry']['coordinates'].append(location)
                                    
                                    if loom:
                                        route_point_el = stop_point.find('./n:projections/n:PointProjection/n:ProjectToPointRef', self.ns)
                                        if route_point_el is not None and 'ref' in route_point_el.attrib:
                                            loom_route_points.append({
                                                'point':route_point_el.attrib['ref'],
                                                'stopplace':stop_points_geodata['features'][point_id]['properties']['stopplace']
                                            })


                        if quay and time_tracker:
                            arrival = time_tracker.strftime("%H:%M:%S")

                            if wait_time is not None:
                                time_tracker = time_tracker + wait_time

                            departure = time_tracker.strftime("%H:%M:%S")

                            if driving_time is not None:
                                time_tracker = time_tracker + driving_time

                            if index == 0:
                                journey_timestamps.append(quay_properties | {
                                    'arrival':None,
                                    'departure':departure
                                })
                            elif index + 1 == len(points):
                                journey_timestamps.append(quay_properties | {
                                    'arrival':arrival,
                                    'departure':None
                                })
                            else:
                                journey_timestamps.append(quay_properties | {
                                    'arrival':arrival,
                                    'departure':departure
                                })


                        if loom:
                            journey_loom_geodata = {}
                            for index, loom_route_point in enumerate(loom_route_points):
                                if index == 0: continue
                                if loom_route_points[index - 1]['stopplace'] is None or loom_route_point['stopplace'] is None: break
                                loom_route_link_id = f'{loom_route_points[index - 1]['point']} - {loom_route_point['point']}'
                                loom_line_id = f'{loom_route_points[index - 1]['point']} - {loom_route_point['stopplace']}'
                                if loom_route_link_id not in loom_route_links: 
                                    # print(f'LOOM: Geodata incompleet voor {loom_route_point['stopplace']}')
                                    continue
                                journey_loom_geodata['line_'+loom_line_id] = {
                                    "type": "Feature",
                                    "geometry": {
                                        "type": "LineString",
                                        "coordinates": loom_route_links[loom_route_link_id]
                                    },
                                    "properties":{
                                        'from':loom_route_points[index - 1]['stopplace'],
                                        'to':loom_route_point['stopplace'],
                                        'lines':[]
                                    }
                                }
                            
                            if len(list(journey_loom_geodata.keys())) == len(list(loom_route_points)) - 1:
                                for key in journey_loom_geodata:
                                    inserted_data = loom_geodata.setdefault(key, journey_loom_geodata[key])
                                    
                                    if journey_data['line_id'] not in list(map(lambda x: x['id'], inserted_data['properties']['lines'])):
                                        loom_geodata[key]['properties']['lines'].append({
                                            'color':self.loom_line_color(journey_data['line_id']),
                                            'id':journey_data['line_id'],
                                            'label':journey_data['line_number']
                                        })

                        def add_line_properties(properties, line_data):
                            if journey_data['line_number'] is not None:
                                stop_points_geodata['features'][point_id]["properties"]["line_numbers"].add(journey_data['line_number'])

                            if journey_data['line_name'] is not None:
                                properties["lines"].add(journey_data['line_name'])

                            if 'mode_of_transport' in line_data and line_data['mode_of_transport'] is not None:
                                properties["modes_of_transport"].add(line_data['mode_of_transport'])

                            if 'sub_mode_of_transport' in line_data and line_data['sub_mode_of_transport'] is not None:
                                properties["sub_modes_of_transport"].add(line_data['sub_mode_of_transport'])

                            if 'line_code' in line_data and line_data['line_code'] is not None:
                                properties["line_codes"].add(line_data['line_code'])

                            if 'formula' in line_data and line_data['formula'] is not None:
                                properties["formulas"].add(line_data['formula'])

                            if 'type_of_product' in line_data and line_data['type_of_product'] is not None:
                                properties["types_of_product"].add(line_data['type_of_product'])

                            if 'operator' in line_data and line_data['operator'] is not None:
                                properties["operators"].add(line_data['operator'])

                            if 'network' in line_data and line_data['network'] is not None:
                                properties["networks"].add(line_data['network'])

                            return properties
                        stop_points_geodata['features'][point_id]["properties"] = add_line_properties(stop_points_geodata['features'][point_id]["properties"], line_data)

                    if time_tracker:
                        time_in_service['to'] = time_tracker
                        journey_data['dru'] = (time_in_service['to'] - time_in_service['from']).total_seconds() / 3600

            self.notice_able_ids.append(journey_data['id'])

            validity_conditions = {}

            if journey.find('./n:validityConditions', self.ns) is not None and availability_conditions is not None:
                refs = journey.findall('./n:validityConditions/n:AvailabilityConditionRef', self.ns)
                for ref in refs:
                    condition = availability_conditions.find(f"./n:AvailabilityCondition[@id='{ref.attrib['ref']}']", self.ns)
                    condition_data = {
                        'id':ref.attrib['ref'],
                        'from':None,
                        'through':None,
                        'bits':None
                    }
                    if condition is not None:
                        condition_from = condition.find('./n:FromDate', self.ns)
                        if condition_from is not None: condition_data['from'] = condition_from.text
                        condition_through = condition.find('./n:ToDate', self.ns)
                        if condition_through is not None: condition_data['through'] = condition_through.text
                        condition_bits = condition.find('./n:ValidDayBits', self.ns)
                        if condition_bits is not None: condition_data['bits'] = condition_bits.text

                        validity_conditions.setdefault(ref.attrib['ref'], condition_data)

            owner_operator_el = journey.find('./n:keyList/n:KeyValue[n:Key="DataOwnerIsOperator"]', self.ns)
            if owner_operator_el is not None:
                owner_operator = owner_operator_el.find('./n:Value', self.ns)
                if owner_operator is not None:
                    journey_data['in_scope_of_operator'] = owner_operator.text == 'true'

            journey_number_el = journey.find(f'./n:privateCodes/n:PrivateCode[@type="JourneyNumber"]', self.ns)
            if journey_number_el is not None: journey_data['number'] = journey_number_el.text

            realtime_info_el = journey.find(f'./n:Monitored', self.ns)
            if realtime_info_el is not None: journey_data['realtime_info'] = (realtime_info_el.text == 'true')

            journeys_df = pd.DataFrame.from_dict(
                dict(list(map(
                    lambda x: (x, [journey_data[x]]),
                    journey_data.keys()
                )))
            )

            if time_table:
                con = sqlite3.connect(f'{output_folder}/netex.db')

                journeys_df.to_sql('journeys', con, if_exists='append', index=False, dtype={'id':'STRING PRIMARY KEY'})

                journey_timestamps_df = pd.DataFrame.from_records(journey_timestamps)
                journey_timestamps_df.insert(0, 'journey', '')
                journey_timestamps_df['journey'] = journey_data['id']
                journey_timestamps_df.to_sql('journey_timestamps', con, if_exists='append', index=False)
                cur = con.cursor()
                cur.execute('CREATE TABLE IF NOT EXISTS availabilities (id TEXT PRIMARY KEY, available_from TEXT, available_through TEXT, bits TEXT)')
                cur.executemany("INSERT OR REPLACE INTO availabilities VALUES (?, ?, ?, ?)", list(map(
                    lambda x: (x['id'], x['from'], x['through'], x['bits']),
                    validity_conditions.values()
                )))
                cur.execute('CREATE TABLE IF NOT EXISTS availabilities_per_journey (id INTEGER PRIMARY KEY, journey TEXT NOT NULL, availability TEXT NOT NULL, line TEXT NOT NULL)')
                cur.executemany("INSERT OR REPLACE INTO availabilities_per_journey VALUES (?, ?, ?, ?)", list(map(
                    lambda x: (None, journey_data['id'], x['id'], journey_data['line_id']),
                    validity_conditions.values()
                )))
                con.commit()

            # time_demand_type_ref = journey.find('./n:TimeDemandTypeRef', self.ns)
            # if time_demand_type_ref is not None and time_demand_types is not None:
            #     ref = time_demand_type_ref.attrib['ref']
            #     time_demand = time_demand_types.find(f'./n:TimeDemandType[@id="{ref}"]', self.ns)
                con.close()

        stop_points_geodata['features'] = list(stop_points_geodata['features'].values())

        def modifyFeature(x):
            x["properties"]["line_numbers"] = ", ".join(list(x["properties"]["line_numbers"]))
            x["properties"]["lines"] = " | ".join(map(lambda x: x.replace(' | ', ' \| '), list(x["properties"]["lines"])))
            x["properties"]["modes_of_transport"] = ", ".join(list(x["properties"]["modes_of_transport"]))
            x["properties"]["sub_modes_of_transport"] = ", ".join(list(x["properties"]["sub_modes_of_transport"]))
            x["properties"]["line_codes"] = ", ".join(list(x["properties"]["line_codes"]))
            x["properties"]["formulas"] = ", ".join(list(x["properties"]["formulas"]))
            x["properties"]["types_of_product"] = ", ".join(list(x["properties"]["types_of_product"]))
            x["properties"]["operators"] = ", ".join(list(x["properties"]["operators"]))
            x["properties"]["networks"] = ", ".join(list(x["properties"]["networks"]))
            return x
        
        stop_points_geodata['features'] = list(map(modifyFeature, stop_points_geodata['features']))

        if loom:
            for feautre in stop_points_geodata['features']:
                stop_place_code = feautre['properties']['stopplace']
                if f'stop_{stop_place_code}' in loom_geodata: continue

                if feautre['properties']['stopplace'] is None: continue

                loom_feature = copy.deepcopy(feautre)
                loom_feature['geometry']['type'] = 'Point'
                loom_feature['geometry']['coordinates'] = feautre['geometry']['coordinates'][0]
                loom_feature['properties'] = {
                    'id':feautre['properties']['stopplace'],
                    'station_id':feautre['properties']['stopplace'],
                    'station_label':feautre['properties']['stopplace_name']
                }

                if not loom_feature['properties']['station_label']:
                    loom_feature['properties']['station_label'] = feautre['properties']['name']

                loom_geodata[f'stop_{stop_place_code}'] = loom_feature

            loom_file_data = {"type": "FeatureCollection",'features':list(reversed(loom_geodata.values()))}

            if crs not in ['wgs84', 'EPSG:4326']:
                loom_file_data = gpd.GeoDataFrame.from_features(loom_file_data).set_crs(crs).to_json(na='drop', to_wgs84=True)
            else:
                loom_file_data = json.dumps(loom_file_data)

            file_count = list(filter(
                lambda x: x.startswith('loom'),
                os.listdir(output_folder)
            ))
            
            open(f'{output_folder}/loom_{len(file_count)}.json', 'w').write(loom_file_data)


        if len(stop_points_geodata['features']) == 0: return

        stop_points_gdf = gpd.GeoDataFrame.from_features(
            features=stop_points_geodata
        ).set_crs(crs).to_crs(self.defaults['crs'])

        stop_points_gdf.to_file(f'{output_folder}/netex.gpkg', layer="scheduled_stop_points", driver="GPKG", mode="a")

    def getNotices(self, service:ET.Element, only_used=True):
        notices = service.find('./n:notices', self.ns)
        notice_assignments = service.find('./n:noticeAssignments', self.ns)

        if notices is None or notice_assignments is None: return

        for assignment in notice_assignments.findall('./*', self.ns):
            notice_for_el = assignment.find('./n:NoticedObjectRef', self.ns)
            if notice_for_el is None or 'ref' not in notice_for_el.attrib: continue
            notice_for = notice_for_el.attrib['ref']

            if only_used and notice_for not in self.notice_able_ids: continue

            notice_id_el = assignment.find('./n:NoticeRef', self.ns)
            if notice_id_el is None or 'ref' not in notice_id_el.attrib: continue
            notice_id = notice_id_el.attrib['ref']

            notice_text_el = notices.find(f'./n:Notice[@id="{notice_id}"]/n:Text',self.ns)
            if notice_text_el is None: continue
            notice_text = notice_text_el.text

            con = sqlite3.connect(f'{output_folder}/netex.db')
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, note_for TEXT NOT NULL, content TEXT NOT NULL, name TEXT)')
            cur.execute("INSERT OR REPLACE INTO notices (id, note_for, content) VALUES (?, ?, ?)", (notice_id, notice_for, notice_text))
            con.commit()
            con.close()

            

    def get(self, layers=[]):
        data = {}

        for layer in layers:
            try:
               data[layer] = gpd.read_file(f'{output_folder}/netex.gpkg', layer=layer)
            except:
                pass 

        return data
        

    defaults = {
        'datasource':None,
        'datasource_code':None,
        'crs':4326, # 4326 = wgs84
    }

    loom_line_colors = {}
    def loom_line_color(self, id):
        if id in self.loom_line_colors: return self.loom_line_colors[id]
        r = lambda: random.randint(0, 255)
        self.loom_line_colors[id] = '#%02X%02X%02X' % (r(), r(), r())
        return self.loom_line_colors[id]

    notice_able_ids = []

    def __init__(self, file = None, str_content = None, enum_list=None, epiap_list=None, options={}):
        if file is None and str_content is None:
            raise Exception('File or string required')

        if not os.path.exists(output_folder):
            os.mkdir(output_folder)
        
        if file is not None:
            tree = ET.parse(file)
            self.root = tree.getroot()
        else:
            tree = ET.fromstring(str_content)
            self.root = tree
        
        if enum_list is not None:
            enum_list = list(map(lambda x: ET.fromstring(x), enum_list))

        self.ns = {
            'n':'http://www.netex.org.uk/netex',
            'gml':"http://www.opengis.net/gml/3.2"
        }

        self.options = options

        compositeFrames = self.root.findall('./n:dataObjects/n:CompositeFrame', self.ns)

        for compositeFrame in compositeFrames:
            resource = compositeFrame.find('./n:frames/n:ResourceFrame', self.ns)
            service = compositeFrame.find('./n:frames/n:ServiceFrame', self.ns)
            timetable = compositeFrame.find('./n:frames/n:TimetableFrame', self.ns)
            serviceCalendar = compositeFrame.find('./n:frames/n:ServiceCalendarFrame', self.ns)
            vehicleSchedule = compositeFrame.find('./n:frames/n:VehicleScheduleFrame', self.ns)

            defualts = compositeFrame.find('./n:FrameDefaults', self.ns)
            if defualts is not None:
                def_datasource_el = defualts.find('./n:DefaultDataSourceRef', self.ns)
                if def_datasource_el is not None and 'ref' in def_datasource_el.attrib and resource is not None:
                    datasource_el = resource.find(f'./n:dataSources/n:DataSource[@id="{def_datasource_el.attrib['ref']}"]', self.ns)
                    if datasource_el is not None:
                        name_el = datasource_el.find('./n:Name', self.ns)
                        if name_el is not None:
                            self.defaults['datasource'] = name_el.text

                        short_name_el = datasource_el.find('./n:ShortName', self.ns)
                        if short_name_el is not None:
                            self.defaults['datasource_code'] = short_name_el.text

            df_crs = 'wgs84'
            found_crs = compositeFrame.find('./n:FrameDefaults/n:DefaultLocationSystem', self.ns)
            if found_crs is not None:
                df_crs = found_crs.text

            if service is None: continue

            self.rotues = self.craftRoutes(service=service, resource=resource, timetable=timetable, enum_list=enum_list, crs=df_crs)

            if timetable is None: continue

            self.journeys = self.craftJourneys(service=service, resource=resource, timetable=timetable, enum_list=enum_list, epiap_list=epiap_list, crs=df_crs)

            self.getNotices()

        return
