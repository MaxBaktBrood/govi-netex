import typing
import pandas as pd
import geopandas as gpd
import json
import sqlite3
from datetime import datetime, timedelta
import copy
import holidays
import os

data_folder = './output'
output_folder = './output'

def no_special_characters(str = ""):
    new_str = ''
    for char in str:
        if char.isalpha() or char.isdigit():
            new_str += char
        else:
            new_str += '_'
    return new_str

class NetexJSON:

    lines_per_network = {}

    def line_information(self):
        if not 'routes' in self.geo_tables: return
        routes = self.geo_tables['routes']

        processed = {}

        for line_id in routes['line_id'].unique():

            line_routes = routes[routes['line_id']==line_id]

            line = {
                "code": line_routes['line_code'].iloc[0],
                "line_name": line_routes['line_name'].iloc[0],
                "line_number": line_routes['line_number'].iloc[0],
                "line_mode_of_transport": line_routes['mode_of_transport'].iloc[0],
                "type": None,
                "routes": None,
                "notes": {}
            }

            self.lines_per_network.setdefault(line_routes['network_id'].iloc[0], {
                'name':line_routes['network'].iloc[0],
                'lines':[]
            })

            self.lines_per_network[line_routes['network_id'].iloc[0]]['lines'].append(line_id)

            con = sqlite3.connect(f'{output_folder}/netex.db')
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, note_for TEXT NOT NULL, content TEXT NOT NULL, name TEXT)')
            line['notes'] = dict(cur.execute("SELECT id, content FROM notices WHERE note_for = ?", (line_id,)).fetchall())
            con.close()

            line_type = line_routes['type_of_product'].iloc[0]
            if line_type is None:
                line_type = line_routes['formula'].iloc[0]
            
            line['type'] = line_type

            # line['routes'] = json.loads(line_routes[['id', 'direction']].to_json())['features'] #replaced by next line
            line['routes'] = json.loads(routes[routes['line_id'] == line_id].to_json(drop_id=True))['features']
            for route in line['routes']:
                route['properties'] = {
                    'route':route['properties']['id'],
                    'direction':route['properties']['direction']
                }

            processed.setdefault(line_id, line)

        return processed
    
    def divide_lines_by_network(self, lines:dict):
        divided = []
        for network in self.lines_per_network:
            network_data = copy.deepcopy(self.lines_per_network[network])
            network_data['id'] = network

            def modify_line(x):
                line = copy.copy(lines[x])
                del line['routes']
                del line['notes']
                return line

            network_data['lines'] = list(map(
                modify_line,
                list(set(network_data['lines']))
            ))

            divided.append(network_data)
        
        return divided
    
    def divided_lines_per_region(self, divided_lines:list, region_per_line_code:dict):
        def divide_network(network):
            network = copy.copy(network)
            network['parts'] = {}
            for line in network['lines']:
                part = 'unknown'
                if line['code'] in region_per_line_code:
                    part = region_per_line_code[line['code']]
                else:
                    #print(line['code'])
                    pass
                
                part_entry = network['parts'].setdefault(part, {
                    'name':part,
                    'lines':[]
                })

                part_entry['lines'].append(line)
            
            del network['lines']
            network['parts'] = list(network['parts'].values())

            return network

        return list(map(
            divide_network, divided_lines
        ))

    def cut_availabilities(self, validity_periods):
        cutting_points = set()
        line_group = {}

        for validity in validity_periods:
            validity['from'] = validity.pop('available_from')
            validity['through'] = validity.pop('available_through')
            cutting_points.add(datetime.fromisoformat(validity['from']))
            cutting_points.add(datetime.fromisoformat(validity['through']) + timedelta(days=1))

        cutting_points = list(cutting_points)

        for validity in validity_periods:
            v_from = datetime.fromisoformat(validity['from'])
            v_to = datetime.fromisoformat(validity['through'])

            cut_from = copy.copy(v_from)
            cut_bits = ''

            counter = copy.copy(v_from)

            for bit in validity['bits']:
                if counter in cutting_points and cut_bits != '':
                    v_from = cut_from
                    v_to = (counter - timedelta(days=1))
                    
                    original_id = line_group.setdefault(validity['id'], {})
                    original_id[
                        f'{v_from.strftime('%d-%m-%Y')}-{v_to.strftime('%d-%m-%Y')}'
                    ] = {
                        'from':v_from.isoformat(),
                        'through':v_to.isoformat(),
                        'bits':cut_bits
                    }

                    cut_from = copy.copy(counter)
                    cut_bits = ''

                cut_bits += bit
                counter = counter + timedelta(days=1)
            
            if cut_bits != '':
                v_from = cut_from
                v_to = (counter - timedelta(days=1))
                original_id = line_group.setdefault(validity['id'], {})
                original_id[
                    f'{v_from.strftime('%d-%m-%Y')}-{v_to.strftime('%d-%m-%Y')}'
                ] = {
                    'from':v_from.isoformat(),
                    'through':v_to.isoformat(),
                    'bits':cut_bits
                }
        
        return line_group

    known_validities = {}

    def validity_summary(self, validity):
        validity_period = f'{validity['from']}-{validity['through']}'

        if validity_period in self.known_validities:
            known_period = self.known_validities[validity_period]
            if validity['bits'] in known_period:
                return known_period[validity['bits']]
        
        validity_per_weekday = {
            'monday':{},
            'tuesday':{},
            'wednesday':{},
            'thursday':{},
            'friday':{},
            'saturday':{},
            'sun- and holidays':{}
        }

        from_date = datetime.fromisoformat(validity['from'])
        date_tracker = copy.copy(from_date)

        for bit in validity['bits']:
            weekday = date_tracker.weekday()

            dutch_holidays = holidays.NL(language='nl')
            if date_tracker in dutch_holidays:
                weekday = 6
                # controversial: shouldn't all holidays be included in sun- and holidays?
                if dutch_holidays.get(date_tracker) == 'Koningsdag' or dutch_holidays.get(date_tracker) == 'Koninginnedag':
                    weekday = 5

            validity_per_weekday[list(validity_per_weekday.keys())[weekday]].setdefault(date_tracker.strftime('%d-%m-%Y'), int(bit))
            date_tracker = date_tracker + timedelta(days=1)

        ratio_per_weekday = {}

        for weekday in validity_per_weekday:
            values = list(validity_per_weekday[weekday].values())
            ratio = 0
            if len(values) > 0:
                ratio = sum(values) / len(values)
            ratio_per_weekday[weekday] = ratio

        ratios_per_category = {
            'monday through friday':sum(list(ratio_per_weekday.values())[:5]) / 5,
            'saturday':list(ratio_per_weekday.values())[5],
            'sun- and holidays':list(ratio_per_weekday.values())[6]
        }

        workdays_excepted = set()
        workday_exceptions = []

        if ratios_per_category['monday through friday'] > 0:
            for weekday in list(ratio_per_weekday.keys())[:5]:
                ratio = ratio_per_weekday[weekday]

                if ratio == 0:
                    workday_exceptions.append({
                        "type":"NOT",
                        "day":weekday
                    })
                    workdays_excepted.add(weekday)

        excluding_dates = {
            "monday through friday":[],
            "saturday":[],
            "sun- and holidays":[]
        }
        including_dates = {
            "monday through friday":[],
            "saturday":[],
            "sun- and holidays":[]
        }
            
        for weekday in validity_per_weekday:
            validities_per_date = validity_per_weekday[weekday]

            for date in validities_per_date:
                if weekday in workdays_excepted: continue

                category = copy.copy(weekday)
                if category != 'saturday' and category != 'sun- and holidays':
                    category = 'monday through friday'

                if ratio_per_weekday[weekday] < 0.5 and validities_per_date[date] == 1:
                    including_dates[category].append(date)
                if ratio_per_weekday[weekday] >= 0.5 and validities_per_date[date] == 0:
                    excluding_dates[category].append(date)

        summary = {
            "monday through friday":None,
            "saturday":None,
            "sun- and holidays":None
        }

        for category in ratios_per_category:
            if ratios_per_category[category] == 0: 
                # summary[category] = []
                continue

            exceptions = []
            if category == "monday through friday":
                exceptions = exceptions + workday_exceptions

            dates = sorted(
                including_dates[category],
                key=lambda x: datetime.strptime(x, '%d-%m-%Y')
            )
            if len(dates) > 0:
                exceptions.append({
                    "type":"ONLY",
                    "dates":dates
                })

            dates = sorted(
                excluding_dates[category],
                key=lambda x: datetime.strptime(x, '%d-%m-%Y')
            )
            if len(dates) > 0:
                exceptions.append({
                    "type":"NOT",
                    "dates":dates
                })

            summary[category] = exceptions

        known_period = self.known_validities.setdefault(
            validity_period, {}
        )
        known_period[validity['bits']] = summary

        return summary
     
    def line_timetable(self, line_id):
        con = sqlite3.connect(f'{data_folder}/netex.db')
        cur = con.cursor()

        availabilities = cur.execute("SELECT * FROM availabilities WHERE id IN (SELECT availability FROM availabilities_per_journey WHERE line = ?)", (line_id,)).fetchall()

        availabilities = list(map(
                lambda x: {
                    'id':x[0],
                    'available_from':x[1],
                    'available_through':x[2],
                    'bits':x[3],
                }
        , availabilities))

        availabilities = self.cut_availabilities(availabilities)

        entry = {
            "quays":{},
            "journey_notes":{},
            "timetable":{}
        }


        for row in cur.execute("SELECT * FROM journeys WHERE line_id = ?", (line_id,)).fetchall():
            journey = dict(zip((
                "id","number","route","line_id","in_scope_of_operator","distance","dru","direction","line_name","line_number","network","network_id","network_code","realtime_info",
            ), row))
            # line = journeys_per_line.setdefault(journey['line_id'], {})
            # line[journey['id']] = journey
            applied_availability_keys = cur.execute("SELECT availability FROM availabilities_per_journey WHERE journey = ?", (journey['id'],)).fetchall()

            departures = cur.execute("SELECT quay_name, quay_code, quay_location, arrival, departure FROM journey_timestamps WHERE journey = ?", (journey['id'],)).fetchall()
            departures = list(map(
                lambda x: {
                    'quay_name':x[0],
                    'quay_code':x[1],
                    'quay_location':list(map(lambda x: float(x), x[2].split(','))),
                    'arrival':x[3],
                    'departure':x[4],
                },
                departures
            ))

            cur.execute('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, note_for TEXT NOT NULL, content TEXT NOT NULL, name TEXT)')
            journey_notes = dict(cur.execute("SELECT id, content FROM notices WHERE note_for = ?", (journey['id'],)).fetchall())
            entry['journey_notes'] = entry['journey_notes'] | journey_notes

            applied_availabilities = [
                x for xs in list(map(
                lambda key: list(availabilities[key[0]].values()),
                applied_availability_keys
                )) for x in xs
            ]
            
            for index, validity in enumerate(applied_availabilities):
                validity_period = entry['timetable'].setdefault(
                    f'validity_{index}', validity | {"directions":{}}
                )
                direction_key = validity_period['directions'].setdefault(journey['direction'], {})

                exceptions_per_category = self.validity_summary(validity)
                for category_key in exceptions_per_category:
                    if exceptions_per_category[category_key] == None:
                        category = direction_key.setdefault(category_key, {
                            'exceptions':exceptions_per_category[category_key],
                            'quays':{}
                        })
                        continue

                    category = direction_key.setdefault(category_key, {
                        'exceptions':exceptions_per_category[category_key],
                        'quays':{}
                    })

                    for index, departure in enumerate(departures):
                        quay = category['quays'].setdefault(departure['quay_code'], {})

                        quay_in_entry = entry['quays'].setdefault(departure['quay_code'], {
                            'quay_name':departure['quay_name'],
                            'quay_code':departure['quay_code'],
                            'quay_location':departure['quay_location'],
                            'known_orders':{}
                        })
                        quay_direction_orders = quay_in_entry['known_orders'].setdefault(
                            journey['direction'], {}
                        )
                        index_count = quay_direction_orders.setdefault(index, 0)
                        quay_direction_orders[index] += 1

                        if departure['departure']:
                            quay[departure['departure']] = {
                                'journey_number':journey['number'],
                                'notes':list(journey_notes.keys()),
                                # 'vehicle_type':journey['vehicle_type'],
                                'route':journey['route']
                            }
                        elif departure['arrival']:
                            quay[departure['arrival']] = {
                                'journey_number':journey['number'],
                                'notes':list(journey_notes.keys()),
                                # 'vehicle_type':journey['vehicle_type'],
                                'route':journey['route']
                            }

                # journey_stops = direction.setdefault(journey['number'], {
                #     "departures":journey['departures'],
                #     "categories":validity_summary(validity)
                # })
        
        con.close()

        quays_overview = []
        quay_order = {}
        for quay in entry['quays']:

            for key in entry['quays'][quay]['known_orders']:
                def avg(list = []):
                        return sum(list) / len(list)
                order = avg(
                    [
                        z
                        for zs in map(
                            lambda x: [x[0]] * x[1],
                            entry['quays'][quay]['known_orders'][key].items()
                        )
                        for z in zs
                    ]
                )
                
                quay_order.setdefault(key, {})
                quay_order[key][quay] = order

            del entry['quays'][quay]['known_orders']

            quays_overview.append(
                {'id':quay} | entry['quays'][quay]
            )
        entry['quays'] = quays_overview

        for direction in quay_order:
            quay_order[direction] = list(map(
                lambda x: x[0],
                sorted(quay_order[direction].items(),
                key=lambda y: y[1])
            ))

        validity_list = []

        for validity in entry['timetable']:
            validity_details = entry['timetable'][validity]
            directions = copy.copy(validity_details['directions'])
            del validity_details['directions'] # not required because of overwrite but to make it clear
            direction_lists = []

            for direction_key in directions:
                periods = directions[direction_key]
                period_lists = []

                for period_key in periods:
                    period = periods[period_key]
                    quays = period['quays']
                    quay_list = []

                    if len(quays) == 0:
                        period['quays'] = quay_list

                        period_lists.append({
                            'period':period_key
                        } | period)

                        continue

                    period['journey_numbers'] = []

                    for quay_key in quays:
                        quay = quays[quay_key]
                        for timestamp in quay:
                            period['journey_numbers'].append(quay[timestamp]['journey_number'])

                    period['journey_numbers'] = sorted(list(set(period['journey_numbers'])))

                    period['journey_notes'] = [None] * len(period['journey_numbers'])

                    period['journey_routes'] = [None] * len(period['journey_numbers'])

                    for quay_key in quay_order[direction_key]:
                        if not quay_key in quays:
                            quay_list.append(None)
                            continue

                        quay = quays[quay_key]
                        timestamp_list = list(map(lambda _: None, period['journey_numbers']))

                        for timestamp in quay:
                            timestamp_list[
                                period['journey_numbers'].index(quay[timestamp]['journey_number'])
                            ] = datetime.strptime(timestamp, "%H:%M:%S").strftime("%H:%M")

                            period['journey_notes'][
                                period['journey_numbers'].index(quay[timestamp]['journey_number'])
                            ] = quay[timestamp]['notes']

                            period['journey_routes'][
                                period['journey_numbers'].index(quay[timestamp]['journey_number'])
                            ] = quay[timestamp]['route']
                            

                        # timestamp_list = sorted(
                        #     list(map(
                        #         lambda x: datetime.strptime(x, "%H:%M:%S").strftime("%H:%M"),
                        #         list(quays[quay_key].keys())
                        #     )),
                        #     key=lambda x: datetime.strptime(x, "%H:%M")
                        # )

                        quay_list.append({
                            'quay':quay_key,
                            'timestamps':timestamp_list
                        })
                    
                    period['quays'] = quay_list

                    period_lists.append({
                        'period':period_key
                    } | period)

                direction_lists.append({
                    'direction':direction_key,
                    'periods':period_lists
                })
            
            validity_list.append(
                validity_details | {'directions':direction_lists}
            )
        
        entry['timetable'] = validity_list
    
        return entry

                 
    def to_json(self, lines=None):
        if not os.path.exists(f'{output_folder}/json-timetables'):
            os.mkdir(f'{output_folder}/json-timetables')

        if lines is None:
            lines = self.line_information()

        for line in lines:
            filename = None
            if os.path.exists(f'{output_folder}/json-timetables/{lines[line]['code']}'):
                filename = no_special_characters(line)
            else:
                filename = lines[line]['code']
            
            line_json = {'line':lines[line]} | self.line_timetable(line)

            open(f'{output_folder}/json-timetables/{filename}.json', 'w').write(json.dumps(line_json))
        

        
        


        

    def __init__(self):
        self.geo_tables = {
            'routes':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='routes'),
            'routepoints':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='routepoints'),
            'scheduled_stop_points':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='scheduled_stop_points'),
        }



