import geopandas as gpd
import os
import orjson as json

input_areas = './input_options/areas.gpkg'

loom_file = './output/loom.json'

def split_loom_by_area():
    if not os.path.exists(input_areas) or not os.path.exists(loom_file): return

    areas = gpd.read_file(input_areas).to_crs('wgs84')

    split_files = []

    for area in areas.itertuples():
        split_files.append({
            "type": "FeatureCollection",
            "features": []
        })

    loom = json.loads(open(loom_file, 'rb').read())

    for feature in loom['features']:
        feature_gdf = gpd.GeoDataFrame.from_features([feature]).set_crs('wgs84')['geometry'].iloc[0]

        if feature['geometry']['type'] == "Point":
            for file in split_files: file['features'].append(feature)
            continue

        for index, overlap in enumerate(areas.geometry.intersects(feature_gdf, align=True).to_list()):
            if overlap:
                split_files[index]['features'].append(feature)

    for index, file in enumerate(split_files):
        open(f'./output/split_loom_{str(index)}.json', 'wb').write(json.dumps(file))


if __name__ == '__main__':
    split_loom_by_area()