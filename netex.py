from lxml import etree as ET
import os
from zoneinfo import ZoneInfo
from pyproj import Transformer
from netex_processing.nl import NetexNL


class Netex:

   
    defaults = {
        'datasource':None,
        'datasource_code':None,
        'responsibility_set':None,
        'from_crs':4326,
        'to_crs':4326, # 4326 = wgs84,
        'timezone':ZoneInfo('UTC'),
        'frametype':{'general':None, 'specific':None},
        'output_folder':'./output'
    }

    def __init__(self, file = None, str_content = None, enum_list=None, options={}):
        if file is None and str_content is None:
            raise Exception('File or string required')

        if not os.path.exists(self.defaults['output_folder']):
            os.mkdir(self.defaults['output_folder'])

        parser = ET.XMLParser(ns_clean=True)
        
        if file is not None:
            tree = ET.parse(file, parser)
            self.root = tree.getroot()
        else:
            tree = ET.fromstring(str_content, parser)
            self.root = tree
        
        if enum_list is not None:
            enum_list = list(map(lambda x: ET.fromstring(x), enum_list))

        self.ns = {
            'n':'http://www.netex.org.uk/netex',
            'gml':"http://www.opengis.net/gml/3.2"
        }

        self.options = options

        self.transformer = None

        compositeFrames = self.root.findall('./n:dataObjects/n:CompositeFrame', self.ns)

        enum_frames = []

        for compositeFrame in compositeFrames:
            general = compositeFrame.find('./n:frames/n:GeneralFrame', self.ns)
            resource = compositeFrame.find('./n:frames/n:ResourceFrame', self.ns)
            service = compositeFrame.find('./n:frames/n:ServiceFrame', self.ns)
            timetable = compositeFrame.find('./n:frames/n:TimetableFrame', self.ns)
            serviceCalendar = compositeFrame.find('./n:frames/n:ServiceCalendarFrame', self.ns)
            vehicleSchedule = compositeFrame.find('./n:frames/n:VehicleScheduleFrame', self.ns)
            site = compositeFrame.find('./n:frames/n:SiteFrame', self.ns)

            frametype_el = compositeFrame.find('./n:TypeOfFrameRef', self.ns)
            if frametype_el is None:
                print('No frametype!')
            else:
                self.defaults['frametype'] = {
                    'general':frametype_el.attrib['ref'].split(':')[0],
                    'specific':frametype_el.attrib['ref']
                }

            defualts = compositeFrame.find('./n:FrameDefaults', self.ns)
            if defualts is not None:
                def_datasource_el = defualts.find('./n:DefaultDataSourceRef', self.ns)
                if def_datasource_el is not None and 'ref' in def_datasource_el.attrib and resource is not None:
                    datasource_el = resource.find(f'./n:dataSources/n:DataSource[@id="{def_datasource_el.attrib["ref"]}"]', self.ns)
                    if datasource_el is not None:
                        name_el = datasource_el.find('./n:Name', self.ns)
                        if name_el is not None:
                            self.defaults['datasource'] = name_el.text

                        short_name_el = datasource_el.find('./n:ShortName', self.ns)
                        if short_name_el is not None:
                            self.defaults['datasource_code'] = short_name_el.text
                
                def_responsibility_el = defualts.find('./n:DefaultResponsibilitySetRef', self.ns)
                if def_responsibility_el is not None and 'ref' in def_responsibility_el.attrib:
                    self.defaults['responsibility_set'] = def_responsibility_el.attrib['ref']


            found_crs = compositeFrame.find('./n:FrameDefaults/n:DefaultLocationSystem', self.ns)
            if found_crs is not None:
                self.defaults['from_crs'] = found_crs.text

            if self.defaults['from_crs'] != self.defaults['to_crs']:
                self.transformer = Transformer.from_crs(self.defaults['from_crs'], self.defaults['to_crs'])

            found_timezone = compositeFrame.find('./n:FrameDefaults/n:DefaultLocale/n:TimeZone', self.ns)
            if found_timezone is not None:
                self.defaults['timezone'] = ZoneInfo(found_timezone.text)

            if service is None: 
                if general is not None or resource is not None or site is not None:
                    enum_frames.append(compositeFrame)
                continue

            processer = None

            match self.defaults['frametype']['general']:
                case 'NL':
                    processer = NetexNL(self.defaults, self.options, self.ns, self.transformer)
                case _:
                    processer = NetexNL(self.defaults, self.options, self.ns, self.transformer)


            self.rotues = processer.craftRoutes(service=service, resource=resource, timetable=timetable, site=site, enum_list=enum_list)

            if timetable is None: continue

            self.journeys = processer.craftJourneys(service=service, resource=resource, timetable=timetable, general_frame=general, enum_list=enum_list)

            processer.getNotices(service=service)

            processer.db_indexes()

        if len(enum_frames) > 0: processer.enum_frames(enum_frames)

        if processer.cur: processer.cur.close()
        if processer.con: processer.con.close()
            

