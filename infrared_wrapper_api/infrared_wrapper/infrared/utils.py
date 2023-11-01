import geopandas as gpd
import json

# gets a values from a nested object
def get_value(data, path):
    for prop in path:
        if len(prop) == 0:
            continue
        if prop.isdigit():
            prop = int(prop)
        data = data[prop]
    return data


def reproject_geojson(geojson_in: dict, source_crs, target_crs) -> dict:
    gdf = gpd.GeoDataFrame.from_features(geojson_in)
    gdf = gdf.set_crs(source_crs, allow_override=True)

    return json.loads(gdf.to_crs(target_crs).to_json())