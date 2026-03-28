import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
import typing

class Netex:
    

    def craftRoutes(self, service:ET.Element, resource:ET.Element | None=None, enum_list:list[ET.Element]| None=None, crs='wgs84'):
        routes = service.find('./n:routes', self.ns)

        if routes is None: return print('Geen routedata')

        for route in routes:
            line_ref = route.find('./n:LineRef', self.ns).attrib['ref']
            line = service.find(f"./n:lines/n:Line[@id='{line_ref}']", self.ns)

            points = route.find('./n:pointsInSequence', self.ns)

            if points is None: continue

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
                

            route_data = {
                'id':route.attrib['id'],
                'line_id':line.attrib['id'],
                'mode_of_transport':None,
                'line_number':None,
                'line_name':None,
                'line_code':None,
                'direction':None,
                'formula':None,
                'authority':None,
                'authority_code':None,
                'operator':None,
                'operator_code':None,
                'network':None,
                'network_code':None,
            }

            mode_of_transport_el = line.find('./n:TransportMode', self.ns)
            if mode_of_transport_el is not None:
                route_data['mode_of_transport'] = mode_of_transport_el.text
            
            line_number_el = line.find('./n:PublicCode', self.ns)
            if line_number_el is not None:
                route_data['line_number'] = line_number_el.text
            
            line_name_el = line.find('./n:Name', self.ns)
            if line_name_el is not None:
                route_data['line_name'] = line_name_el.text
            
            line_code_el = line.find('./n:privateCodes/n:PrivateCode', self.ns)
            if line_code_el is not None:
                route_data['line_code'] = line_code_el.text

            branding_ref_el = line.find('./n:BrandingRef', self.ns)
            if branding_ref_el and resource is not None:
                branding_ref = branding_ref_el.attrib['ref']
                branding_el = resource.find(f"./n:typesOfValue/n:Branding[@id='{branding_ref}']", self.ns)
                if branding_el is not None:
                    name = branding_el.find('./n:Name', self.ns)
                    if name is not None:
                        route_data['formula'] = name.text

            authority_ref_el = line.find('./n:AuthorityRef', self.ns)
            if authority_ref_el and resource is not None:
                authority_ref = authority_ref_el.attrib['ref']

                if enum_list:
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

                if route_data['authority'] is None:
                    route_data['authority'] = authority_ref

            operator_ref_el = line.find('./n:OperatorRef', self.ns)
            if operator_ref_el is not None and resource is not None:
                operator_ref = operator_ref_el.attrib['ref']
                operator_el = resource.find(f"./n:organisations/n:Operator[@id='{operator_ref}']", self.ns)
                if operator_el is not None:
                    name_el = operator_el.find('./n:Name', self.ns)
                    if name_el is not None: route_data['operator'] = name_el.text
                    code_el = operator_el.find('./n:ShortName', self.ns)
                    if code_el is not None: route_data['operator_code'] = code_el.text

            if 'responsibilitySetRef' in line.attrib:
                responsibility_el = resource.find(f"./n:responsibilitySets/n:ResponsibilitySet[@id='{line.attrib['responsibilitySetRef']}']/n:roles", self.ns)
                if responsibility_el is not None:
                    for role in responsibility_el:
                        roletypes = role.find('./n:StakeholderRoleType', self.ns)
                        organisation = role.find('./n:StakeholderRoleType', self.ns)

                        if roletypes is not None and 'EntityLegalOwnership' in roletypes.text.split(' '):
                            area = role.find('./n:ResponsibleAreaRef', self.ns)

                            if area is not None and enum_list is not None:
                                for enum in enum_list:
                                    compositeFrames = enum.findall('./n:dataObjects/n:CompositeFrame', self.ns)
                                    for compositeFrame in compositeFrames:
                                        area_el = compositeFrame.find(f"./n:frames/n:GeneralFrame/n:members/n:TransportAdministrativeZone[@id='{area.attrib['ref']}']", self.ns)
                                        if area_el is not None:
                                            name = area_el.find('./n:Name', self.ns)
                                            if name is not None:
                                                route_data['network'] = name.text
                                            code = area_el.find('./n:ShortName', self.ns)
                                            if code is not None:
                                                route_data['network_code'] = code.text

                            if route_data['network'] is None:
                                route_data['Network'] = area.attrib['ref']

            
            direction_el = route.find('./n:DirectionType', self.ns)
            if direction_el is not None:
                route_data['direction'] = direction_el.text
                


            line_geodata['properties'] = route_data
            points_geodata['properties'] = route_data

            line_gdf = geopandas.GeoDataFrame.from_features(
                features=[line_geodata]
            ).set_crs(crs)

            line_gdf.to_file('netex.gpkg', layer="routes", driver="GPKG", mode="a")

            points_gdf = geopandas.GeoDataFrame.from_features(
                features=[points_geodata]
            ).set_crs(crs)

            points_gdf.to_file('netex.gpkg', layer="routepoints", driver="GPKG", mode="a")
        
        return

    def __init__(self, file = None, str_content = None, enum_list=None, epiap_list=None):
        if file is None and str_content is None:
            raise Exception('File or string required')
        
        if file is not None:
            tree = ET.parse(file)
            self.root = tree.getroot()
        else:
            tree = ET.fromstring(str_content)
            self.root = tree

        if epiap_list is not None:
            epiap_list = list(map(lambda x: ET.fromstring(x), epiap_list))
        
        if enum_list is not None:
            enum_list = list(map(lambda x: ET.fromstring(x), enum_list))

    
        self.ns = {
            'n':'http://www.netex.org.uk/netex',
            'gml':"http://www.opengis.net/gml/3.2"
        }

        compositeFrames = self.root.findall('./n:dataObjects/n:CompositeFrame', self.ns)

        for compositeFrame in compositeFrames:
            resource = compositeFrame.find('./n:frames/n:ResourceFrame', self.ns)
            service = compositeFrame.find('./n:frames/n:ServiceFrame', self.ns)
            timetable = compositeFrame.find('./n:frames/n:TimetableFrame', self.ns)
            serviceCalendar = compositeFrame.find('./n:frames/n:ServiceCalendarFrame', self.ns)
            vehicleSchedule = compositeFrame.find('./n:frames/n:VehicleScheduleFrame', self.ns)

            df_crs = 'wgs84'
            found_crs = compositeFrame.find('./n:FrameDefaults/n:DefaultLocationSystem', self.ns)
            if found_crs is not None:
                df_crs = found_crs.text

            if service is None: continue

            self.rotues = self.craftRoutes(service=service, resource=resource, enum_list=enum_list, crs=df_crs)

        return
