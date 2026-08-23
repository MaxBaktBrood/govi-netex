from lxml import etree as ET
import pygml
from typing import Optional
from datetime import datetime
import isodate
import sqlite3
from dataclasses import dataclass, fields, astuple, asdict
from netex_processing.dataclasses import Branding, ProductType, Operator, Authority, Area, RelResponsibilityArea, Line, Route, RelPointRoute, Routepoint, Routelink, Runtime, Waittime, TimingLink, RelTimingRoutePoint, Pattern, PointInPattern, ScheduledStopPoint, StopArea, AvailabilityCondition, Journey, AvailabilityPerJourney, RelStoppointQuaycode, RelQuayStopplace, Stopplace, Notice

class NetexNL:

    def to_db(self, name, dataclass, data={}):
            
            cols = []            
            for field in fields(dataclass):
                sql_part = f'{field.name}'

                if field.type == str:
                    sql_part += ' TEXT NOT NULL'
                elif field.type == int:
                    sql_part += ' INTEGER NOT NULL'
                elif field.type == float:
                    sql_part += ' REAL NOT NULL'
                elif field.type == Optional[str]:
                    sql_part += ' TEXT'
                elif field.type == Optional[int]:
                    sql_part += ' INTEGER'
                elif field.type == Optional[float]:
                    sql_part += ' REAL'
                
                if field.name == 'id': sql_part += ' PRIMARY KEY'

                cols.append(sql_part)
            
            if not self.con: self.con = sqlite3.connect(f'{self.defaults['output_folder']}/netex.db')
            if not self.cur: self.cur = self.con.cursor()

            self.cur.execute(f'CREATE TABLE IF NOT EXISTS {name} ({", ".join(cols)})')

            if len(data) == 0: 
                self.con.commit()
                return #print(f'{name} heeft geen data')

            self.cur.executemany(f'INSERT OR REPLACE INTO {name} VALUES ({", ".join(['?'] * len(list(cols)))})',
                list(map(
                    lambda x: astuple(x),
                    list(data.values())
                ))
            )

            self.con.commit()

            # if len(data) == 0: return print(f'{name} heeft geen data')
            # df = pd.DataFrame.from_records(list(data.values()))

            # if 'id' in df: 
            #     existing_ids = pd.read_sql(
            #         'SELECT '
            #     )
            # df.to_sql(
            #     name, self.con, if_exists='append', index=False,
            #     dtype={'id':'STRING PRIMARY KEY'}
            # )
    
    def db_indexes(self):
        if not self.cur: self.cur = self.con.cursor()
        self.cur.execute('CREATE INDEX IF NOT EXISTS runtimes_time_demand ON runtimes(time_demand_type, timing_link);')
        self.cur.execute('CREATE INDEX IF NOT EXISTS waittimes_time_demand ON waittimes(time_demand_type, scheduled_stop_point, timing_point);')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_availabilities_per_journey ON availabilities_per_journey(journey);')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_point_route ON rel_point_route(route);')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_responsibility_area ON rel_responsibility_area(responsibility);')
        # self.cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_stoppoint_quaycode ON rel_stoppoint_quaycode(stoppoint);')
        self.con.commit()

    def date_to_iso(self, text):
        return datetime.fromisoformat(text).replace(tzinfo=self.defaults['timezone']).isoformat()
    
    def get_brandings(self, resource:ET.Element):
        brandings: dict[str, Branding] = {}

        
        for branding_el in resource.findall(f"./n:typesOfValue/n:Branding", self.ns):
            branding = Branding(branding_el.attrib['id'])
            name = branding_el.find('./n:Name', self.ns)
            if name is not None:
                branding.name = name.text
            
            url = branding_el.find('./n:Url', self.ns)
            if url is not None:
                branding.url = url.text
            
            brandings[branding.id] = branding

        self.to_db('brandings', Branding, brandings)
        
    def get_product_types(self, resource:ET.Element):
        product_types: dict[str, ProductType] = {}
        
        

        for product_el in resource.findall(f"./n:typesOfValue/n:TypeOfProductCategory", self.ns):
            product = ProductType(product_el.attrib['id'], None)
            name = product_el.find('./n:Name', self.ns)
            if name is not None:
                product.name = name.text
            
            product_types[product.id] = product
        
        self.to_db('product_types', ProductType, product_types)
    
    def get_operators(self, resource:ET.Element):
        operators: dict[str, Operator] = {}

        for operator_el in resource.findall(f"./n:organisations/n:Operator", self.ns):
            operator = Operator(operator_el.attrib['id'], None, None)
            name_el = operator_el.find('./n:Name', self.ns)
            if name_el is not None: operator.name = name_el.text
            code_el = operator_el.find('./n:ShortName', self.ns)
            if code_el is not None: operator.code = code_el.text
            operators[operator.id] = operator

            self.known_ids['operators'].append(operator.id)
        
        self.to_db('operators', Operator, operators)
    
    def get_authorities(self, resource:ET.Element):
        authorities: dict[str, Authority] = {}

        for authority_el in resource.findall(f'./n:organisations/n:Authority', self.ns):
            authority_data = Authority(authority_el.attrib['id'])
            name = authority_el.find('./n:Name', self.ns)
            if name is not None:
                authority_data.name = name.text
            code = authority_el.find('./n:ShortName', self.ns)
            if code is not None:
                authority_data.code = code.text
            authorities[authority_data.id] = authority_data
        
        self.to_db('authorities', Authority, authorities)

    def get_areas(self, general_frame:ET.Element):
        areas: dict[str, Area] = {}

        for area_el in general_frame.findall(f"./n:members/n:TransportAdministrativeZone", self.ns):
            area_data = Area(area_el.attrib['id'])
            name = area_el.find('./n:Name', self.ns)
            if name is not None:
                area_data.name = name.text
            code = area_el.find('./n:ShortName', self.ns)
            if code is not None:
                area_data.code = code.text

            areas[area_data.id] = area_data
        
        self.to_db('areas', Area, areas)

    def get_rel_responsibility_area(self, resource:ET.Element):
        rel_responsibility_area: dict[str, RelResponsibilityArea] = []

        for role in resource.findall(f"./n:responsibilitySets/n:ResponsibilitySet/n:roles", self.ns):
            for responsibility in role.findall('./n:ResponsibilityRoleAssignment', self.ns):
                role_data = RelResponsibilityArea(role.find('..').attrib['id'])

                area = responsibility.find('./n:ResponsibleAreaRef', self.ns)
                if area is not None:
                    role_data.area_ref = area.attrib['ref']

                    rel_responsibility_area.append(role_data)
        
        self.to_db('rel_responsibility_area', RelResponsibilityArea, dict(
            (str(i), x) for i, x in enumerate(rel_responsibility_area)
        ))

    def get_lines(self, service:ET.Element, resource:ET.Element):
        lines: dict[str, Line] = {}

        for line in service.findall('./n:lines/n:Line', self.ns):
            line_data = Line(
                line.attrib['id'], 
                responsibility_set=self.defaults['responsibility_set']
            )

            mode_of_transport_el = line.find('./n:TransportMode', self.ns)
            if mode_of_transport_el is not None:
                line_data.transport_mode = mode_of_transport_el.text
                if 'translate_to_dutch' in self.options and self.options['translate_to_dutch'] is True:
                    match line_data.transport_mode:
                        case 'bus': line_data.transport_mode = 'bus'
                        case 'rail': line_data.transport_mode = 'trein'
                        case 'tram': line_data.transport_mode = 'tram'
                        case 'metro': line_data.transport_mode = 'metro'
                        case 'water': line_data.transport_mode = 'water'
            
            sub_modes_of_transport = line.findall('./n:TransportSubmode/*', self.ns)
            if len(sub_modes_of_transport) > 0:
                line_data.transport_sub_mode = ", ".join(
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
                    line_data.transport_sub_mode = ", ".join(dutch_modes)            

            line_number_el = line.find('./n:PublicCode', self.ns)
            if line_number_el is not None:
                line_data.number = line_number_el.text
            
            line_name_el = line.find('./n:Name', self.ns)
            if line_name_el is not None:
                line_data.name = line_name_el.text
            
            line_code_el = line.find('./n:PrivateCode[@type="LinePlanningNumber"]', self.ns)
            if line_code_el is None:
                line_code_el = line.find('./n:PrivateCode', self.ns)
            if line_code_el is not None:
                line_data.code = line_code_el.text

            if line_data.code and 'linecode_categories' in self.options:
                if str(line_data.code) in self.options['linecode_categories']:
                    line_data.custom_category = self.options['linecode_categories'][str(line_data.code)]
                else: line_data.custom_category = None
            
            branding_ref_el = line.find('./n:BrandingRef', self.ns)
            if branding_ref_el is not None:
                line_data.branding = branding_ref_el.attrib['ref']
            
            product_type_ref_el = line.find('./n:TypeOfProductCategoryRef', self.ns)
            if product_type_ref_el is not None and resource is not None:
                line_data.type_of_product = product_type_ref_el.attrib['ref']

            authority_ref_el = line.find('./n:AuthorityRef', self.ns)
            if authority_ref_el is not None:
                line_data.authority = authority_ref_el.attrib['ref']

            operator_ref_el = line.find('./n:OperatorRef', self.ns)
            if operator_ref_el is None:
                operator_ref_el = line.find('./n:additionalOperators/n:OperatorRef', self.ns) 
            if operator_ref_el is not None and resource is not None:
                line_data.operator = operator_ref_el.attrib['ref']
            else:
                if self.defaults['datasource'] not in self.known_ids['operators']:
                    self.to_db('operators', Operator, {
                        self.defaults['datasource']:Operator(self.defaults['datasource'],
                            self.defaults['datasource_code'],
                            self.defaults['datasource']
                            )
                    })

                line_data.operator = self.defaults['datasource']

            if 'responsibilitySetRef' in line.attrib:
                line_data.responsibility_set = line.attrib['responsibilitySetRef']

            
            type_of_service_ref_el = line.find('./n:TypeOfServiceRef', self.ns)
            if type_of_service_ref_el is not None:
                line_data.type_of_service = type_of_service_ref_el.attrib['ref']

            lines[line_data.id] = line_data

        self.to_db('lines', Line, lines)

    def get_routes(self, service:ET.Element):
        routes: dict[str, Route] = {}

        rel_point_route: list[RelPointRoute] = []

        for route in service.findall('./n:routes/n:Route', self.ns):
            route_data = Route(route.attrib['id'])

            line_ref_el = route.find('./n:LineRef', self.ns)
            if line_ref_el is not None: route_data.line = line_ref_el.attrib['ref']

            direction_el = route.find('./n:DirectionType', self.ns)
            if direction_el is not None:
                route_data.direction = direction_el.text
                if 'translate_to_dutch' in self.options and self.options['translate_to_dutch'] is True:
                    match route_data.direction:
                        case 'outbound': route_data.direction = 'uitgaand'
                        case 'inbound': route_data.direction = 'inkomend'
            
            points = route.findall('./n:pointsInSequence/*', self.ns)
            if points is None: continue

            for index, point in enumerate(points):
                order = index
                if 'order' in point.attrib:
                    order = int(point.attrib['order'])

                routepoint_ref = point.find('./n:RoutePointRef', self.ns).attrib['ref']
                routelink_ref = None

                routelink_el = point.find('./n:OnwardRouteLinkRef', self.ns)
                if routelink_el is not None:
                    routelink_ref = routelink_el.attrib['ref']
                
                rel_point_route.append(RelPointRoute(
                    route_data.id, order,
                    routepoint_ref, routelink_ref
                ))
            
            routes[route_data.id] = route_data
        
        self.to_db('rel_point_route', RelPointRoute, dict(
            (str(i), x) for i, x in enumerate(rel_point_route)
        ))
        self.to_db('routes', Route, routes)

    def get_routepoints(self, service:ET.Element):
        routepoints: dict[str, Routepoint] = {}

        for point in service.findall(f"./n:routePoints/n:RoutePoint", self.ns):
            routepoint_data = Routepoint(point.attrib['id'])
            routepoint_location = point.find(f"./n:Location", self.ns)

            if routepoint_location is None: continue
            gml = routepoint_location.find("./gml:pos", self.ns)

            if gml is not None:
                routepoint_data.location = gml.text
                # routepoint_data['location'] = list(pygml.basics.parse_pos(gml.text))
            else:
                lng = routepoint_location.find('./n:Longitude', self.ns)
                lat = routepoint_location.find('./n:Latitude', self.ns)

                if lng is not None and lat is not None:
                    routepoint_data.location = " ".join([lng.text, lat.text])

            if routepoint_data.location is not None and self.transformer is not None:
                routepoint_data.location = ' '.join(
                    map(str, self.transformer.transform(*routepoint_data.location.split(' ')))
                )


            routepoints[routepoint_data.id] = routepoint_data
        
        self.to_db('routepoints', Routepoint, routepoints)

    def get_routelinks(self, service:ET.Element):
        routelinks: dict[str, Routelink] = {}

        for link in service.findall(f"./n:routeLinks/n:RouteLink", self.ns):
            link_data = Routelink(link.attrib['id'])

            routelink = pygml.parse(ET.tostring(link.find(f"./gml:LineString", self.ns)))
            coords = dict(routelink.__geo_interface__)['coordinates']

            if routelink is not None and self.transformer is not None:
                coords = (self.transformer.transform(*x) for x in coords)


            link_data.location = " ".join(" ".join(map(str, x)) for x in coords)

            routelinks[link_data.id] = link_data
        
        self.to_db('routelinks', Routelink, routelinks)

    def get_run_waittimes(self, service:ET.Element):
        runtimes: dict[str, Runtime] = {} 
        waittimes: dict[str, Waittime]  = {}
        

        for time_demand_type in service.findall('./n:timeDemandTypes/n:TimeDemandType', self.ns):
            for runtime in time_demand_type.findall('./n:runTimes/n:JourneyRunTime', self.ns):
                if 'id' not in runtime.attrib: continue
                runtime_data = Runtime(runtime.attrib['id'], time_demand_type.attrib['id'])

                time_el = runtime.find('./n:RunTime', self.ns)

                if time_el is not None:
                    runtime_data.time = isodate.parse_duration(time_el.text).total_seconds()

                timing_link_el = runtime.find('./n:TimingLinkRef', self.ns)
                if timing_link_el is not None and 'ref' in timing_link_el.attrib:
                    runtime_data.timing_link = timing_link_el.attrib['ref']
                
                runtimes[runtime_data.id] = runtime_data

            for waittime in time_demand_type.findall('./n:waitTimes/n:JourneyWaitTime', self.ns):
                if 'id' not in waittime.attrib: continue
                waittime_data = Waittime(waittime.attrib['id'], time_demand_type.attrib['id'])

                time_el = waittime.find('./n:WaitTime', self.ns)

                if time_el is not None:
                    waittime_data.time = isodate.parse_duration(time_el.text).total_seconds()

                stop_point_el = waittime.find('./n:ScheduledStopPointRef', self.ns)
                if stop_point_el is not None and 'ref' in stop_point_el.attrib:
                    waittime_data.scheduled_stop_point = stop_point_el.attrib['ref']
                
                timing_point_el = waittime.find('./n:TimingPointRef', self.ns)
                if timing_point_el is not None and 'ref' in timing_point_el.attrib:
                    waittime_data.timing_point = timing_point_el.attrib['ref']
                
                waittimes[waittime_data.id] = waittime_data

        self.to_db('runtimes', Runtime, runtimes)
        self.to_db('waittimes', Waittime, waittimes)

    def get_timing_links(self, service:ET.Element):
        timing_links: dict[str, TimingLink] = {}
        
        for timing_link in service.findall('./n:timingLinks/n:TimingLink', self.ns):
            timing_link_data = TimingLink(timing_link.attrib['id'])
            distance_el = timing_link.find('./n:Distance', self.ns)
            if distance_el is not None:
                distance = float(distance_el.text)
                timing_link_data.distance += distance
        
            timing_links[timing_link_data.id] = timing_link_data

        self.to_db('timing_links', TimingLink, timing_links)

    def get_rel_timing_route_points(self, service:ET.Element):
        rel_timing_route_points: list[RelTimingRoutePoint] = []

        for timing_point in service.findall('./n:timingPoints/n:TimingPoint', self.ns):
            route_point_el = timing_point.find('./n:projections/n:PointProjection/n:ProjectToPointRef', self.ns)
            if route_point_el is not None and 'ref' in route_point_el.attrib:
                rel_timing_route_points.append(RelTimingRoutePoint(
                    timing_point.attrib['id'],
                    route_point_el.attrib['ref']
                ))
        
        self.to_db('rel_timing_route_points', RelTimingRoutePoint, dict(
            (str(i), x) for i, x in enumerate(rel_timing_route_points)
        ))
    
    def get_patterns(self, service:ET.Element):
        patterns: dict[str, Pattern] = {}
        points_in_pattern: dict[str, PointInPattern] = {}
        
        
        for pattern in service.findall('./n:journeyPatterns/n:ServiceJourneyPattern', self.ns):
            pattern_data = Pattern(pattern.attrib['id'])

            routeref_el = pattern.find('./n:RouteRef', self.ns)
            if routeref_el is not None:
                pattern_data.route = routeref_el.attrib['ref']

            direction_el = pattern.find('./n:DirectionType', self.ns)
            if direction_el is not None:
                direction = direction_el.text
                pattern_data.direction = direction
            
            points = pattern.findall('./n:pointsInSequence/*', self.ns)
            for index, point in enumerate(points):
                point_data = PointInPattern(point.attrib['id'], pattern_data.id, index)

                timingpoint_ref = point.find('./n:TimingPointRef', self.ns)
                if timingpoint_ref is not None:
                    point_data.timing_point = timingpoint_ref.attrib['ref']

                stoppoint_ref = point.find('./n:ScheduledStopPointRef', self.ns)
                if stoppoint_ref is not None:
                    point_data.stoppoint = stoppoint_ref.attrib['ref']
                timing_link_ref = point.find('./n:OnwardTimingLinkRef', self.ns)
                if timing_link_ref is not None:
                    point_data.timing_link = timing_link_ref.attrib['ref']
                
                points_in_pattern[point_data.id] = point_data
            
            patterns[pattern_data.id] = pattern_data
        
        self.to_db('patterns', Pattern, patterns)
        self.to_db('points_in_pattern', PointInPattern, points_in_pattern)

    def get_scheduled_stop_points(self, service:ET.Element):
        scheduled_stop_points: dict[str, ScheduledStopPoint] = {}

        for stop_point in service.findall('./n:scheduledStopPoints/n:ScheduledStopPoint', self.ns):
            if 'id' not in stop_point.attrib: continue
            stop_point_data = ScheduledStopPoint(stop_point.attrib['id'])

            stop_area_ref_el = stop_point.find("./n:stopAreas/n:StopAreaRef", self.ns)
            if stop_area_ref_el is not None:
                stop_point_data.stop_area = stop_area_ref_el.attrib['ref']

            route_point_ref_el = stop_point.find("./n:projections/n:PointProjection/n:ProjectToPointRef", self.ns)
            if route_point_ref_el is not None:
                stop_point_data.route_point = route_point_ref_el.attrib['ref']

            stop_point_name = stop_point.find("./n:Name", self.ns)
            if stop_point_name is not None:
                stop_point_data.name = stop_point_name.text
            
            stop_point_location = stop_point.find("./n:Location", self.ns)
            if stop_point_location is not None:
                gml = stop_point_location.find("./gml:pos", self.ns)

                if gml is not None:
                    stop_point_data.location = " ".join(str(x) for x in list(pygml.basics.parse_pos(gml.text)))
                else:
                    lng = stop_point_location.find('./n:Longitude', self.ns)
                    lat = stop_point_location.find('./n:Latitude', self.ns)

                    if lng is not None and lat is not None:
                        stop_point_data.location = " ".join([lng.text, lat.text])

            if stop_point_data.location is not None and self.transformer is not None:
                
                stop_point_data.location = ' '.join(
                    map(str, self.transformer.transform(*stop_point_data.location.split(' ')))
                )

            scheduled_stop_points[stop_point_data.id] = stop_point_data
        
        self.to_db('scheduled_stop_points', ScheduledStopPoint, scheduled_stop_points)

    def get_stop_areas(self, service:ET.Element):
        stop_areas: dict[str, StopArea] = {}

        for stop_area in service.findall('./n:stopAreas/n:StopArea', self.ns):
            stop_area_data = StopArea(stop_area.attrib['id'])

            name_el = stop_area.find("./n:Name", self.ns)
            if name_el is not None: 
                stop_area_data.name = name_el.text

            public_name_el = stop_area.find("./n:PublicCode", self.ns)
            if public_name_el is not None: 
                stop_area_data.public_code = public_name_el.text

            code_el = stop_area.find("./n:privateCodes/n:PrivateCode[@type='UserStopAreaCode']", self.ns)
            if code_el is not None: stop_area_data.private_code = code_el.text

            place_el = stop_area.find("./n:TopographicPlaceView/n:Name", self.ns)
            if place_el is not None: stop_area_data.place_name = place_el.text

            stop_areas[stop_area_data.id] = stop_area_data

        self.to_db('stop_areas', StopArea, stop_areas)

    def get_validity_conditions(self, timetable:ET.Element):
        validity_conditions: dict[str, AvailabilityCondition] = {}
        
        for condition in timetable.findall('./n:contentValidityConditions/n:AvailabilityCondition', self.ns):
            condition_data = AvailabilityCondition(condition.attrib['id'])

            condition_from = condition.find('./n:FromDate', self.ns)
            if condition_from is not None: condition_data.available_from = self.date_to_iso(condition_from.text)
            condition_through = condition.find('./n:ToDate', self.ns)
            if condition_through is not None: condition_data.available_through = self.date_to_iso(condition_through.text)
            condition_bits = condition.find('./n:ValidDayBits', self.ns)
            if condition_bits is not None: condition_data.bits = condition_bits.text

            validity_conditions[condition_data.id] = condition_data
        
        self.to_db('validity_conditions', AvailabilityCondition, validity_conditions)

    def get_journeys(self, timetable:ET.Element):
        journeys: dict[str, Journey] = {}
        availabilities_per_journey: list[AvailabilityPerJourney] = []


        for journey in timetable.findall('./n:vehicleJourneys/n:ServiceJourney', self.ns):
            journey_data = Journey(journey.attrib['id'])

            if journey.find('./n:DepartureTime', self.ns) is not None:
                journey_data.starting_time = journey.find('./n:DepartureTime', self.ns).text
            
            time_demand_type_ref = journey.find('./n:TimeDemandTypeRef', self.ns)
            if time_demand_type_ref is not None:
                journey_data.time_demand_type = time_demand_type_ref.attrib['ref']
            
            pattern_ref = journey.find('./n:ServiceJourneyPatternRef', self.ns)
            if pattern_ref is not None: # and patterns is not None
                journey_data.pattern = pattern_ref.attrib["ref"]

            if journey.find('./n:validityConditions', self.ns) is not None:
                refs = journey.findall('./n:validityConditions/n:AvailabilityConditionRef', self.ns)
                for ref in refs:
                    if 'ref' in ref.attrib:
                        availabilities_per_journey.append(
                            AvailabilityPerJourney(journey_data.id, ref.attrib['ref'])
                        )

            owner_operator_el = journey.find('./n:keyList/n:KeyValue[n:Key="DataOwnerIsOperator"]', self.ns)
            if owner_operator_el is not None:
                owner_operator = owner_operator_el.find('./n:Value', self.ns)
                if owner_operator is not None:
                    journey_data.in_scope_of_operator = (owner_operator.text == 'true')

            journey_number_el = journey.find(f'./n:privateCodes/n:PrivateCode[@type="JourneyNumber"]', self.ns)
            if journey_number_el is None:
                journey_number_el = journey.find(f'./n:PrivateCode[@type="JourneyNumber"]', self.ns)

            if journey_number_el is not None: journey_data.number = journey_number_el.text

            realtime_info_el = journey.find(f'./n:Monitored', self.ns)
            if realtime_info_el is not None: journey_data.realtime_info = (realtime_info_el.text == 'true')

            journeys[journey_data.id] = journey_data
        
        self.to_db('journeys', Journey, journeys)
        self.to_db('availabilities_per_journey', AvailabilityPerJourney, dict(
            (str(i), x) for i, x in enumerate(availabilities_per_journey)
        ))

    def get_rel_stoppoint_quaycode(self, service:ET.Element):
        rel_stoppoint_quaycode: dict[str, RelStoppointQuaycode] = {}
        
        for stop in service.findall(f'./n:stopAssignments/n:PassengerStopAssignment', self.ns):
            stop_data = RelStoppointQuaycode()
            stoppoint_el = stop.find(f'./n:ScheduledStopPointRef', self.ns)
            if stoppoint_el is not None and 'ref' in stoppoint_el.attrib:  
                stop_data.id = stoppoint_el.attrib['ref']

            quay_el = stop.find(f'./n:QuayRef', self.ns)
            if quay_el is not None and 'ref' in quay_el.attrib: stop_data.quay = quay_el.attrib['ref'].replace(
                'NL:CHB:quay:','NL:Q:'
            ).replace(
                'NL:CHB:Quay:','NL:Q:'
            )

            rel_stoppoint_quaycode[stop_data.id] = stop_data
        
        self.to_db('rel_stoppoint_quaycode', RelStoppointQuaycode, rel_stoppoint_quaycode)

    def get_stopplaces(self, site:ET.Element):
        rel_quay_stopplace: list[rel_quay_stopplace] = []
        stopplaces: dict[str, Stopplace] = {}

        for stopplace_el in site.findall(f"./n:stopPlaces/n:StopPlace", self.ns):
            code_el = stopplace_el.find('./n:privateCodes/n:PrivateCode[@type="StopPlaceCode"]', self.ns)
            if code_el is None: continue
            
            for quay_el in stopplace_el.findall(f"./n:quays/n:Quay", self.ns):
                quaycode_el = quay_el.find('./n:privateCodes/n:PrivateCode[@type="QuayCode"]', self.ns)
                if quaycode_el is None: continue

                rel_quay_stopplace.append(RelQuayStopplace(code_el.text, quaycode_el.text))

            stopplace_data = Stopplace(code_el.text)

            location_el = stopplace_el.find('./n:Centroid/n:Location/gml:pos', self.ns)
            if location_el is not None:
                stopplace_data.location = location_el.text

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

    def getNotices(self, service:ET.Element, #only_used=True
    ):
        notices = service.find('./n:notices', self.ns)
        notice_assignments = service.find('./n:noticeAssignments', self.ns)

        if notices is None or notice_assignments is None: return

        processed_notices: dict[str, Notice] = {}
        
        for assignment in notice_assignments.findall('./*', self.ns):
            notice_for_el = assignment.find('./n:NoticedObjectRef', self.ns)
            if notice_for_el is None or 'ref' not in notice_for_el.attrib: continue
            notice_for = notice_for_el.attrib['ref']

            # if only_used and notice_for not in self.notice_able_ids: continue

            notice_id_el = assignment.find('./n:NoticeRef', self.ns)
            if notice_id_el is None or 'ref' not in notice_id_el.attrib: continue
            notice_id = notice_id_el.attrib['ref']

            notice_text_el = notices.find(f'./n:Notice[@id="{notice_id}"]/n:Text',self.ns)
            if notice_text_el is None: continue
            notice_text = notice_text_el.text

            processed_notices[notice_id] = Notice(notice_id, notice_for, notice_text)
            
        self.to_db('notices', Notice, processed_notices)  

    def craftRoutes(self, service:ET.Element, resource:Optional[ET.Element]=None, timetable:Optional[ET.Element]=None, general_frame=None, site=None):

        if resource is not None:
            self.get_brandings(resource)
            self.get_product_types(resource)
            self.get_operators(resource)
            self.get_authorities(resource)
            self.get_rel_responsibility_area(resource)
        
        if general_frame is not None: 
            self.get_areas(general_frame)
        
        if service is not None:
            self.get_lines(service, resource)
            self.get_routes(service)
            self.get_routepoints(service)
            self.get_routelinks(service)

        if site is not None:
            self.site_enum(site)   

    
    def craftJourneys(self, service:ET.Element, timetable:ET.Element):

        if service is not None:
            self.get_run_waittimes(service)
            self.get_timing_links(service)
            self.get_timing_links(service)
            self.get_rel_timing_route_points(service)
            self.get_patterns(service)
            self.get_scheduled_stop_points(service)
            self.get_stop_areas(service)
        
        if timetable is not None:
            self.get_validity_conditions(timetable)
            self.get_journeys(timetable)   

    def enum(self, enum_list:list[ET.Element]=[]):
        frames = []
        for enum in enum_list:
            frames.extend(enum.findall('./n:dataObjects/n:CompositeFrame', self.ns))
        self.enum_frames(frames)

    def site_enum(self, site:ET.Element):
        self.get_stopplaces(site)


    def enum_frames(self, compositeFrames:list[ET.Element]=[]):
        authorities = {}
        @dataclass
        class Authority:
            id: str
            name: Optional[str] = None
            code: Optional[str] = None  

        areas = {}
        @dataclass
        class Area:
            id: str
            name: Optional[str] = None
            code: Optional[str] = None

        types_of_service = {}
        @dataclass
        class TypeOfService:
            id: str
            name: Optional[str] = None

        for compositeFrame in compositeFrames:                    
            for authority_el in compositeFrame.findall(f"./n:frames/n:GeneralFrame/n:members/n:Authority", self.ns):
                authority_data = Authority(authority_el.attrib['id'])

                name = authority_el.find('./n:Name', self.ns)
                if name is not None:
                    authority_data.name = name.text
                code = authority_el.find('./n:ShortName', self.ns)
                if code is not None:
                    authority_data.code = code.text
                authorities[authority_data.id] = authority_data

            for area_el in compositeFrame.findall(f"./n:frames/n:GeneralFrame/n:members/n:TransportAdministrativeZone", self.ns):
                area_data = Area(area_el.attrib['id'])

                name = area_el.find('./n:Name', self.ns)
                if name is not None:
                    area_data.name = name.text
                code = area_el.find('./n:ShortName', self.ns)
                if code is not None:
                    area_data.code = code.text

                areas[area_data.id] = area_data

            for type_of_service_el in compositeFrame.findall(f"./n:frames/n:GeneralFrame/n:members/n:ValueSet/n:values/n:TypeOfService", self.ns):
                type_data = TypeOfService(type_of_service_el.attrib['id'])
                
                name = type_of_service_el.find('./n:Name', self.ns)
                if name is not None:
                    type_data.name = name.text
                    types_of_service[type_data.id] = type_data

            if compositeFrame.find(f"./n:frames/n:SiteFrame", self.ns) is not None:
                self.site_enum(compositeFrame.find(f"./n:frames/n:SiteFrame", self.ns))

        self.to_db('authorities', Authority, authorities)
        self.to_db('areas', Area, areas)
        self.to_db('types_of_service', TypeOfService, types_of_service)

        def __init__(self, defaults, options):
            self.defualts = defaults
            self.options = options

    def __init__(self, defaults, options, ns, transformer=None):
        self.known_ids = {
            'operators':[]
        }
        self.con = None
        self.cur = None
        self.defaults = defaults
        self.options = options
        self.transformer = transformer
        self.ns = ns
