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


    def get_journeys_and_patterns(self,service:ET.Element, timetable:ET.Element):
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

                # timingpoint_ref = point.find('./n:TimingPointRef', self.ns)
                # if timingpoint_ref is not None:
                #     point_data.timing_point = timingpoint_ref.attrib['ref']

                stoppoint_ref = point.find('./n:ScheduledStopPointRef', self.ns)
                if stoppoint_ref is not None:
                    point_data.stoppoint = stoppoint_ref.attrib['ref']
                # timing_link_ref = point.find('./n:OnwardTimingLinkRef', self.ns)
                # if timing_link_ref is not None:
                #     point_data.timing_link = timing_link_ref.attrib['ref']
                
                points_in_pattern[point_data.id] = point_data
            
            patterns[pattern_data.id] = pattern_data
        
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
            
            passing_time_els = journey.find('./n:PassingTimes', self.ns)
            for index, passing_time in enumerate(passing_time_els):
                if index + 1 >= len(passing_time_els):
                    continue

                def timeToSeconds(time = ""):
                    time = map(int, time.split(':'))[0:3]
                    time[0] = time[0] * 3600
                    time[1] = time[1]* 60
                    return sum(time)
                
                def getTimes(passing_time:ET.Element):
                    times = {'a':None, 'd':None}
                    arrival_el = passing_time.find('./n:ArrivalTime', self.ns)
                    if arrival_el is not None:
                        times['a'] = timeToSeconds(arrival_el.text)
                    departure_el = passing_time.find('./n:DepartureTime', self.ns)
                    if departure_el is not None:
                        times['d'] = timeToSeconds(departure_el.text)
                    return times
                
                runtime = None
                waittime = None
                
                next_time = getTimes(passing_time_els[index + 1])
                time = getTimes(passing_time)

                point_in_pattern = passing_time.find('./n:StopPointInJourneyPatternRef', self.ns).ref
                next_point_in_pattern = passing_time_els[index + 1].find('./n:StopPointInJourneyPatternRef', self.ns).ref

                if not time['d'] or not next_time['a']: raise Exception('Unexpected timestamps')

                if time['a'] is not None:
                    waittime = Waittime(
                        "_".join([
                            ":".join(point_in_pattern.split(':')[2:]),
                            ":".join(next_point_in_pattern.split(':')[2:]),
                            time['d'] - time['a']
                        ]),
                        "general",
                        points_in_pattern[points_in_pattern].stoppoint,
                        points_in_pattern[points_in_pattern].timing_point,
                        time['d'] - time['a']
                    )
                
                runtime = Runtime(
                    "_".join([
                        ":".join(point_in_pattern.split(':')[2:]),
                        ":".join(next_point_in_pattern.split(':')[2:]),
                        next_time['a'] - time['d']
                    ]),
                    "general",
                    points_in_pattern[points_in_pattern].stoppoint,
                    points_in_pattern[points_in_pattern].timing_point,
                    next_time['a'] - time['d']
                )

                pass

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

        self.to_db('patterns', Pattern, patterns)
        self.to_db('points_in_pattern', PointInPattern, points_in_pattern)


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