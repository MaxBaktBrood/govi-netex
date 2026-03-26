import xml.etree.ElementTree as ET
import geopandas
import pygml
import json
import os
from zipfile import ZipFile
import gzip


class Netex:

    def craftRoutes(self, service = ET.Element, crs='wgs84'):
        routes = service.find('./n:routes', self.ns)

        if routes is None: return print('Geen routedata')

        for route in routes:
            line_ref = route.find('./n:LineRef', self.ns).attrib['ref']
            line = service.find(f"./n:lines/n:Line[@id='{line_ref}']", self.ns)

            points = route.find('./n:pointsInSequence', self.ns)
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

            for point in points:
                routepoint_ref = point.find('./n:RoutePointRef', self.ns).attrib['ref']
                routepoint = list(pygml.basics.parse_pos(service.find(f"./n:routePoints/n:RoutePoint[@id='{routepoint_ref}']/n:Location/gml:pos", self.ns).text))

                points_geodata['geometry']['coordinates'].append(routepoint)
                
                routelink_el = point.find('./n:OnwardRouteLinkRef', self.ns)

                if routelink_el is None: continue
                
                routelink_ref = routelink_el.attrib['ref']
                routelink = pygml.parse(ET.tostring(service.find(f"./n:routeLinks/n:RouteLink[@id='{routelink_ref}']/gml:LineString", self.ns)))
                line_geodata['geometry']['coordinates'].append(dict(routelink.__geo_interface__)['coordinates'])
                

            route_data = {
                'id':route.attrib['id'],
                'line_id':line.attrib['id'],
                'mode_of_transport':line.find('./n:TransportMode', self.ns).text,
                'line_number':line.find('./n:PublicCode', self.ns).text,
                'line_name':line.find('./n:Name', self.ns).text,
                'line_code':line.find('./n:PrivateCode', self.ns).text,
                'direction':route.find('./n:DirectionType', self.ns).text
            }

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

    def __init__(self, file = None, str_content = None):
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

        for compositeFrame in compositeFrames:
            resource = compositeFrame.find('./n:frames/n:ResourceFrame', self.ns)
            service = compositeFrame.find('./n:frames/n:ServiceFrame', self.ns)
            timetable = compositeFrame.find('./n:frames/n:TimetableFrame', self.ns)
            serviceCalendar = compositeFrame.find('./n:frames/n:ServiceCalendarFrame', self.ns)
            vehicleSchedule = compositeFrame.find('./n:frames/n:VehicleScheduleFrame', self.ns)

            df_crs = 'wgs84'
            found_crs = self.root.find('./n:FrameDefaults/n:DefaultLocationSystem', self.ns)
            if found_crs is not None:
                df_crs = found_crs.text

            if service is None: continue

            self.rotues = self.craftRoutes(service=service, crs=df_crs)

        return

INPUT_FOLDER = './input'

if not os.path.isdir(INPUT_FOLDER):
    print('Map gemaakt om bestanden in te zetten: input')
    os.mkdir(INPUT_FOLDER)

for item in os.listdir(INPUT_FOLDER):
    path = os.path.join(INPUT_FOLDER, item)
    
    split_path = os.path.splitext(path)
    print(f'Verwerken van {split_path[0]}')

    if split_path[1] == '.zip':
        netex_zip = ZipFile(path)
        for index, name in enumerate(netex_zip.namelist()):
            print(f'ZIP: Bestand {index}/{len(netex_zip.namelist())}: {name}')
            if os.path.splitext(name)[1] == '.xml':
                file = netex_zip.open(name, 'r')
                content = file.read()
                netex = Netex(str_content=content)


    if split_path[1] == '.gz':
        file = gzip.open(path, 'r')
        content = file.read()
        netex = Netex(str_content=content)


# netex = Netex(file="NeTEx_ARR_NL_20260321_20260322_1405.xml")