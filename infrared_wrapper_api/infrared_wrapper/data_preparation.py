import math
from typing import List

from shapely.geometry import box, Polygon


# creates a matrix of bboxes covering the project area polygon
def create_bbox_matrix(convex_hull_buildings: Polygon, bbox_length) -> List[box]:
    min_x, min_y, max_x, max_y = convex_hull_buildings.bounds
    bbox_matrix = []

    # number of rows and cols of bbox matrix
    max_cols = math.floor((max_x - min_x) / bbox_length) + 1
    max_rows = math.floor((max_y - min_y) / bbox_length) + 1

    for row in range(max_rows):
        box_min_y = min_y + bbox_length * row
        box_max_y = min_y + bbox_length
        for col in range(max_cols):
            box_min_x = min_x + bbox_length * col
            box_max_x = min_x + bbox_length

            # min_x, min_y, max_x, max_y
            bbox = box(box_min_x, box_min_y, box_max_x, box_max_y)
            if convex_hull_buildings.intersection(bbox):
                # only add bbox to matrix, if actually intersecting with the project area polygon
                bbox_matrix.append(bbox)

    return bbox_matrix