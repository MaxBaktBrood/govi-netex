import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip
import requests
import typing

output_folder = './output'

class Netex:
    

    def craftRoutes(self, service:ET.Element, resource:ET.Element | None=None, timetable:ET.Element | None=None, enum_list:list[ET.Element]| None=None, crs='wgs84'):
        routes = service.find('./n:routes', self.ns)

        def line_information(line: ET.Element, route_data={}) -> {}:
            route_data['id'] = line.attrib['id']

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
            if branding_ref_el is not None and resource is not None:
                branding_ref = branding_ref_el.attrib['ref']
                branding_el = resource.find(f"./n:typesOfValue/n:Branding[@id='{branding_ref}']", self.ns)
                if branding_el is not None:
                    name = branding_el.find('./n:Name', self.ns)
                    if name is not None:
                        route_data['formula'] = name.text

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

                            if route_data['network'] is None and area is not None:
                                route_data['Network'] = area.attrib['ref']
        
            return route_data

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
                    route_data = line_information(line, route_data)
                
                # For Germany useless here
                direction_el = pattern.find('./n:DirectionType', self.ns)
                if direction_el is not None:
                    route_data['direction'] = direction_el.text
                    
                line_geodata['properties'] = route_data
                points_geodata['properties'] = route_data

                line_gdf = geopandas.GeoDataFrame.from_features(
                    features=[line_geodata]
                ).set_crs(crs)

                line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

                points_gdf = geopandas.GeoDataFrame.from_features(
                    features=[points_geodata]
                ).set_crs(crs)

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
                    route_data = line_information(line, route_data)

                line_geodata['properties'] = route_data

                line_gdf = geopandas.GeoDataFrame.from_features(
                    features=[line_geodata]
                ).set_crs(crs)
                line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

            return

        if routes is None: 
            return print('Overgeslagen; geen routedata')

        # Original (NETHERLANDS)
        for route in routes:
            line_ref_el = route.find('./n:LineRef', self.ns)
            line_ref = None
            if line_ref_el: line_ref = line_ref_el.attrib['ref']
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
                    
            route_data = {
                'id':route.attrib['id'],
                'line_id':None,
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

            if line is not None:
                route_data = line_information(line, route_data)
            
            direction_el = route.find('./n:DirectionType', self.ns)
            if direction_el is not None:
                route_data['direction'] = direction_el.text
                
            line_geodata['properties'] = route_data
            points_geodata['properties'] = route_data

            line_gdf = geopandas.GeoDataFrame.from_features(
                features=[line_geodata]
            ).set_crs(crs)

            line_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routes", driver="GPKG", mode="a")

            points_gdf = geopandas.GeoDataFrame.from_features(
                features=[points_geodata]
            ).set_crs(crs)

            points_gdf.to_file(f'{output_folder}/netex.gpkg', layer="routepoints", driver="GPKG", mode="a")
        
        return

    def craftJourneys(self, service:ET.Element, timetable:ET.Element, resource:ET.Element|None=None, crs='wgs84'):
        journeys = timetable.find('./n:vehicleJourneys', self.ns)
        patterns = service.find('./n:journeyPatterns', self.ns)
        time_demand_types = service.find('./n:timeDemandTypes', self.ns)
        timing_links = service.find('./n:timingLinks', self.ns)
        stop_points = service.find('./n:scheduledStopPoints', self.ns)
        stop_areas = service.find('./n:stopAreas', self.ns)
        availability_conditions = timetable.find('./n:contentValidityConditions', self.ns)


        stop_points_geodata = {
            "type": "FeatureCollection",
            "features": {}
        }

        if journeys is None: return

        vehicle_types = None
        if resource:
            vehicle_types = resource.find('./n:vehicleTypes', self.ns)

        if journeys is None: return print('Geen ritdata')

        for journey in journeys:

            journey_data = {
                'id':journey.attrib['id'],
                'route':None,
                'available_from':None,
                'available_through':None,
                'available_day_bits':None,
                'in_scope_of_operator':None,
                'number':None,
                'distance':0,
                'direction':None
            }

            if journey.find('./n:validityConditions', self.ns) is not None and availability_conditions is not None:
                refs = journey.findall('./n:validityConditions/n:AvailabilityConditionRef', self.ns)
                for ref in refs:
                    condition = availability_conditions.find(f"./n:AvailabilityCondition[@id='{ref.attrib['ref']}']", self.ns)
                    if condition:
                        condition_from = condition.find('./n:FromDate', self.ns)
                        if condition_from: journey_data['available_from'] = condition_from.text
                        condition_through = condition.find('./n:ToDate', self.ns)
                        if condition_through: journey_data['available_through'] = condition_through.text
                        condition_bits = condition.find('./n:ValidDayBits', self.ns)
                        if condition_bits: journey_data['available_day_bits'] = condition_bits.text

            owner_operator_el = journey.find('./n:keyList/n:KeyValue[n:Key="DataOwnerIsOperator"]', self.ns)
            if owner_operator_el is not None:
                owner_operator = owner_operator_el.find('./n:Value', self.ns)
                if owner_operator is not None:
                    journey_data['in_scope_of_operator'] = (owner_operator.text == 'true')

            journey_number_el = journey.find(f'./n:privateCodes/n:PrivateCode[@id="JourneyNumber"]', self.ns)
            if journey_number_el: journey['number'] = journey_number_el.text

            realtime_info_el = journey.find(f'./n:Monitored', self.ns)
            if realtime_info_el: journey['realtime_info'] = (realtime_info_el.text == 'true')

            pattern_ref = journey.find('./n:ServiceJourneyPatternRef', self.ns)
            if pattern_ref is not None and patterns is not None:
                pattern = patterns.find(f'./n:ServiceJourneyPattern[@id="{pattern_ref.attrib['ref']}"]', self.ns)
                if pattern is not None:
                    routeref_el = pattern.find('./RouteRef', self.ns)
                    if routeref_el is not None:
                        routeref = routeref_el.attrib['ref']
                        journey_data['route'] = routeref
                    
                    direction_el = pattern.find('./n:DirectionType', self.ns)
                    if direction_el is not None:
                        direction = direction_el.text
                        journey_data['direction'] = direction

                    for point in pattern.findall('./n:pointsInSequence/n:StopPointInJourneyPattern', self.ns):
                        timing_link_ref = point.find('./n:OnwardTimingLinkRef', self.ns)
                        if timing_link_ref is not None and timing_links is not None:
                            ref = timing_link_ref.attrib['ref']
                            timing_link = timing_links.find(f'./n:TimingLink[@id="{ref}"]', self.ns)
                            distance_el = timing_link.find('./n:Distance', self.ns)
                            if distance_el is not None:
                                distance = float(distance_el.text)
                                journey_data['distance'] += distance

                        
                        stoppoint_ref = point.find('./n:ScheduledStopPointRef', self.ns)
                        if stoppoint_ref is not None and stop_points is not None and stoppoint_ref.attrib['ref'] not in stop_points_geodata['features']:
                            stop_point: ET.Element = stop_points.find(f'./n:ScheduledStopPoint[@id="{stoppoint_ref.attrib['ref']}"]', self.ns)

                            if stop_point is not None:
                                point_id = None
                                if 'id' in stop_point.attrib:
                                    point_id = stop_point.attrib['id']
                                point_geodata = {
                                    "type": "Feature",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": []
                                    },
                                    "properties":{
                                        "id":point_id,
                                        "name":None,
                                        "line_numbers":set(),
                                        "lines":set(),
                                        "stopplace_name":None,
                                        "stopplace_public_name":None,
                                        "stopplace_code":None,
                                        "place":None
                                    }
                                }

                                stop_point_location = stop_point.find("./n:Location", self.ns)

                                if stop_point_location is not None:
                                    gml = stop_point_location.find("./gml:pos", self.ns)

                                    if gml is not None:
                                        point_geodata['geometry']['coordinates'] = list(pygml.basics.parse_pos(gml.text))
                                    else:
                                        lng = stop_point_location.find('./n:Longitude', self.ns)
                                        lat = stop_point_location.find('./n:Latitude', self.ns)

                                        if lng is not None and lat is not None:
                                            point_geodata['geometry']['coordinates'] = [lng.text, lat.text]

                                stop_point_name = stop_point.find("./n:Name", self.ns)
                                if stop_point_name is not None:
                                    point_geodata['properties']['name'] = stop_point_name.text

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
                                        if code_el is not None: point_geodata['properties']['stopplace_code'] = code_el.text

                                        place_el = stop_area.find("./n:TopographicPlaceView/n:Name", self.ns)
                                        if place_el is not None: point_geodata['properties']['place'] = place_el.text

                        
                                stop_points_geodata['features'].setdefault(point_id, point_geodata)

                        route_ref_el = pattern.find('./n:RouteRef', self.ns)
                        if route_ref_el is not None and 'ref' in route_ref_el.attrib:
                            line_ref_el = service.find(f'./n:routes/n:Route[@id="{route_ref_el.attrib['ref']}"]/n:LineRef', self.ns)
                            if line_ref_el is not None and 'ref' in line_ref_el.attrib:
                                line = service.find(f'./n:lines/n:Line[@id="{line_ref_el.attrib['ref']}"]', self.ns)
                                if line is not None:
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

                                    stop_points_geodata['features'][stoppoint_ref.attrib['ref']]["properties"]["line_numbers"].add(line_number)
                                    stop_points_geodata['features'][stoppoint_ref.attrib['ref']]["properties"]["lines"].add(line_name)

            # time_demand_type_ref = journey.find('./n:TimeDemandTypeRef', self.ns)
            # if time_demand_type_ref is not None and time_demand_types is not None:
            #     ref = time_demand_type_ref.attrib['ref']
            #     time_demand = time_demand_types.find(f'./n:TimeDemandType[@id="{ref}"]', self.ns)

        stop_points_geodata['features'] = list(stop_points_geodata['features'].values())

        def modifyFeature(x):
            x["properties"]["line_numbers"] = list(x["properties"]["line_numbers"])
            x["properties"]["lines"] = list(x["properties"]["lines"])
            return x
        
        stop_points_geodata['features'] = list(map(modifyFeature, stop_points_geodata['features']))

        stop_points_gdf = geopandas.GeoDataFrame.from_features(
            features=stop_points_geodata
        ).set_crs(crs)

        stop_points_gdf.to_file(f'{output_folder}/netex.gpkg', layer="scheduled_stop_points", driver="GPKG", mode="a")




    def __init__(self, file = None, str_content = None, enum_list=None, epiap_list=None):
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

            self.rotues = self.craftRoutes(service=service, resource=resource, timetable=timetable, enum_list=enum_list, crs=df_crs)
            self.journeys = self.craftJourneys(service=service, resource=resource, timetable=timetable, crs=df_crs)

        return
