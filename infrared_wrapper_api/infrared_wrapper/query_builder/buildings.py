from shapely.geometry import Polygon, mapping
from shapely.ops import cascaded_union


# merges adjacent buildings and creates a multipolygon containing all buildings
def merge_adjacent_buildings(geo_json):
    polygons = []
    for feature in geo_json["features"]:
        if feature["geometry"]["type"] == "MultiPolygon":
            polygons.extend(
                Polygon(polygon) for polygon in feature["geometry"]["coordinates"][0]
            )
        else:
            polygons.append(Polygon(feature["geometry"]["coordinates"][0]))
    return {
        "type": "FeatureCollection",
        "features": [{"geometry": mapping(cascaded_union(polygons)), "properties": {}}],
    }


# get sql queries for the buildings
def make_building_queries(buildings_geojson):
    # A multipolygon containing all buildings
    buildings = merge_adjacent_buildings(buildings_geojson)
    sql_insert_strings_all_buildings = []

    for feature in buildings["features"]:
        if "coordinates" not in feature["geometry"]:
            continue
        for polygon in feature["geometry"]["coordinates"]:
            polygon_string = ""
            if not isinstance(polygon[0][0], float):
                # multiple line strings in polygon (i.e. has holes)
                for coordinates_list in polygon:
                    line_string_coordinates = ""
                    try:
                        for coordinate_pair in coordinates_list:
                            # append 0 to all coordinates for mock third dimension
                            coordinate_string = (
                                str(coordinate_pair[0])
                                + " "
                                + str(coordinate_pair[1])
                                + " "
                                + str(0)
                                + ","
                            )
                            line_string_coordinates += coordinate_string
                            # remove trailing comma of last coordinate
                        line_string_coordinates = line_string_coordinates[:-1]
                    except Exception as e:
                        print("invalid json")
                        print(e)
                        print(
                            coordinates_list,
                            coordinate_pair,
                            len(polygon[0]),
                            polygon[0],
                        )
                        print(feature)
                        exit()
                        return ""
                    # create a string containing a list of coordinates lists per linestring
                    #   ('PolygonWithHole', 'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0),(1 1, 1 2, 2 2, 2 1, 1 1))'),
                    polygon_string += f"({line_string_coordinates}),"
            else:
                # only one linestring in polygon (i.e. no holes)
                line_string_coordinates = ""
                try:
                    for coordinate_pair in polygon:
                        # append 0 to all coordinates for mock third dimension
                        coordinate_string = (
                            str(coordinate_pair[0])
                            + " "
                            + str(coordinate_pair[1])
                            + " "
                            + str(0)
                            + ","
                        )
                        line_string_coordinates += coordinate_string
                        # remove trailing comma of last coordinate
                    line_string_coordinates = line_string_coordinates[:-1]
                except Exception as e:
                    print("invalid json")
                    print(e)
                    print(feature)
                    return ""
                # create a string containing a list of coordinates lists per linestring
                polygon_string += f"({line_string_coordinates}),"
            # remove trailing comma of last line string
            polygon_string = polygon_string[:-1]
            sql_insert_string = f"'POLYGON ({polygon_string})'"
            sql_insert_strings_all_buildings.append(sql_insert_string)

    return sql_insert_strings_all_buildings
