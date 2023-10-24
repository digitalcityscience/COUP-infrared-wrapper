def add_third_dimension_to_multi_line_feature(feature):
    for pointList in feature["geometry"]["coordinates"]:
        for point in pointList:
            point.append(0)


def add_third_dimension_to_line_feature(feature):
    for point in feature["geometry"]["coordinates"]:
        point.append(0)


def add_third_dimension_to_features(features):
    for feature in features:
        if feature["geometry"]["type"] == "LineString":
            add_third_dimension_to_line_feature(feature)
        if feature["geometry"]["type"] == "MultiLineString":
            add_third_dimension_to_multi_line_feature(feature)
        # TODO use this for buildings as well
