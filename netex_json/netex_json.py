import typing
import pandas as pd
import geopandas as gpd
import orjson as json
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

    language = 'en'

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
            network_data = copy.copy(self.lines_per_network[network])
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

            cut_from = v_from
            cut_bits = ''

            counter = v_from

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

                    cut_from = counter
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

    def exceptionPresentation(self, exception):
        if not 'type' in exception: return exception
        presentations = {
            'nl':{
                'general':{
                'NOT':'Rijdt niet op',
                'ONLY':'Rijdt alleen op',
                'and':'en'
                },
                'weekdays':{
                    'monday':'maandag', 'tuesday':'dinsdag', 'wednesday':'woensdag', 'thursday':'donderdag', 'friday':'vrijdag', 'saturday':'zaterdag', 'sunday':'zondag'
                }
            },
            'en':{'general':{
                'NOT':'Does not run on',
                'ONLY':'Does only run on',
            }}
        }
        def present(category, key):
            if self.language not in presentations or category not in presentations[self.language] or key not in presentations[self.language][category]:
                return key
            return presentations[self.language][category][key]
        
        if 'day' in exception:
            exception['presentation'] = f'{present('general', exception['type'])} {present('weekdays', exception['day'])}.'
        elif 'dates' in exception:
            dates_to_sentence = copy.copy(exception['dates'])
            if len(dates_to_sentence) > 1:
                last = dates_to_sentence.pop()
                dates_to_sentence = f'{", ".join(dates_to_sentence)} {present('general', 'and')} {last}'
            else: dates_to_sentence = ", ".join(dates_to_sentence)
            exception['presentation'] = f'{present('general', exception['type'])} {dates_to_sentence}.'

        return exception
    
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
        date_tracker = from_date

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

                category = weekday
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

            summary[category] = list(map(lambda x: self.exceptionPresentation(x), exceptions))

        known_period = self.known_validities.setdefault(
            validity_period, {}
        )
        known_period[validity['bits']] = summary

        return summary
     

    def line_timetable(self, line_id):
        con = sqlite3.connect(f'{data_folder}/netex.db')
        cur = con.cursor()

        availabilities = cur.execute("SELECT * FROM availabilities WHERE id IN (SELECT availability FROM availabilities_per_journey WHERE line = ?)", (line_id,)).fetchall()

        availabilities = dict(map(
                lambda x: (x[0], {
                    'available_from':x[1],
                    'available_through':x[2],
                    'bits':x[3],
                })
        , availabilities))

        entry = {
            "quays":{},
            "notes":{},
            "availabilities":availabilities,
            "vehicles":{},
            "timetable":{}
            
        }

        journeys = list(sorted(map(
            lambda x: dict(zip((
                "id","number","route","line_id","in_scope_of_operator","distance","dru","direction","line_name","line_number","network","network_id","network_code","realtime_info",
            ), x))
            , cur.execute("SELECT * FROM journeys WHERE line_id = ?", (line_id,)).fetchall()
        ), key=lambda x: 0 if x['number'] is None else int(x['number'])))

        for journey in journeys:
            applied_availability_keys = list(map(
                lambda x: x[0],
                cur.execute("SELECT availability FROM availabilities_per_journey WHERE journey = ?", (journey['id'],)).fetchall()
            ))
        
            departures = cur.execute("SELECT pattern_point_id, scheduled_point_id, quay_name, quay_code, quay_location, arrival, departure FROM journey_timestamps WHERE journey = ?", (journey['id'],)).fetchall()
            departures = list(map(
                lambda x: {
                    'pattern_point_id':x[0],
                    'scheduled_point_id':x[1],
                    'quay_name':x[2],
                    'quay_code':x[3],
                    'quay_location':list(map(lambda x: float(x), x[4].split(','))),
                    'arrival':x[5],
                    'departure':x[6],
                },
                departures
            ))

            cur.execute('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, note_for TEXT NOT NULL, content TEXT NOT NULL, name TEXT)')
            journey_notes = dict(cur.execute("SELECT id, content FROM notices WHERE note_for = ?", (journey['id'],)).fetchall())
            entry['notes'] = entry['notes'] | journey_notes

            direction = entry['timetable'].setdefault(journey['direction'], {})

            for index, departure in enumerate(departures):
                quay = direction.setdefault(departure['quay_code'], [])

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

                vehicle_index = entry['vehicles'].setdefault('None', # journey['vehicle_type'] ,
                len(entry['vehicles']))

                departure_notes = dict(cur.execute("SELECT id, content FROM notices WHERE note_for = ?", (departure['pattern_point_id'],)).fetchall()
                ) | dict(cur.execute("SELECT id, content FROM notices WHERE note_for = ?", (departure['scheduled_point_id'],)).fetchall())
                entry['notes'] = entry['notes'] | departure_notes

                departure_info = {
                    'arrival':departure['arrival'],
                    'departure':departure['departure'],
                    'order':index,
                    'journey_number':journey['number'],
                    'notes':list(journey_notes.keys()) + list(departure_notes.keys()),
                    'vehicle_type':None, #journey['vehicle_type'],
                    'route':journey['route'],
                    'availabilities':applied_availability_keys
                }

                quay.append(departure_info)

        con.close()
        
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


            open(f'{output_folder}/json-timetables/{filename}.json', 'wb').write(json.dumps(line_json, option=json.OPT_NON_STR_KEYS))
        

        
        


        

    def __init__(self, language=None):
        self.geo_tables = {
            'routes':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='routes'),
            'routepoints':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='routepoints'),
            'scheduled_stop_points':gpd.GeoDataFrame.from_file('./output/netex.gpkg', layer='scheduled_stop_points'),
        }

        self.language = language



