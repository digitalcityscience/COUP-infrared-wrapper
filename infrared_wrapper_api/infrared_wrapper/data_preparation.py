import math
from typing import List
import json

import geopandas as gpd
from shapely.geometry import box
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.models.calculation_input import WindSimulationTask


def create_simulation_tasks(task_def: dict) -> List[WindSimulationTask]:

    buildings_gdf = gpd.GeoDataFrame.from_features(task_def["buildings"]["features"], crs="EPSG:4326")

    # subdivide the region with all buildings into simulation area sized bboxes
    matrix = create_bbox_matrix(buildings_gdf)

    simulation_tasks = []

    for bbox in matrix:
        simulation_tasks.append(WindSimulationTask(
            simulation_area=json.loads(bbox.to_json()),
            buildings=json.loads(buildings_gdf.clip(bbox).to_json()),
            wind_speed=task_def["wind_speed"],
            wind_direction=task_def["wind_direction"],
        ))

    return simulation_tasks


def create_bbox_matrix(buildings: gpd.GeoDataFrame) -> List[gpd.GeoDataFrame]:
    """
    creates a matrix of overlapping bboxes covering the project area polygon
    """
    total_area = buildings.to_crs("EPSG:25832").unary_union.convex_hull  # total area in metric coords
    min_x, min_y, max_x, max_y = total_area.bounds
    size = settings.infrared_calculation.true_simulation_area_size
    buffer = settings.infrared_calculation.simulation_area_buffer

    bbox_matrix = []

    # number of rows and cols of bbox matrix
    max_cols = math.floor((max_x - min_x) / size) + 1
    max_rows = math.floor((max_y - min_y) / size) + 1

    for row in range(max_rows):
        box_min_y = (size * row + min_y) - buffer
        box_max_y = (box_min_y + buffer) + (size + buffer)
        for col in range(max_cols):
            box_min_x = (size * col + min_x) - buffer
            box_max_x = (box_min_x + buffer) + (size + buffer)

            # min_x, min_y, max_x, max_y
            bbox = box(box_min_x, box_min_y, box_max_x, box_max_y)
            _bbox_without_buffer = box(box_min_x + buffer, box_min_y + buffer, box_max_x-buffer, box_max_y-buffer)
            if total_area.intersection(_bbox_without_buffer):
                # only add bbox to matrix, if actually intersecting with the project area polygon
                bbox_matrix.append(gpd.GeoDataFrame(geometry=[bbox], crs="EPSG:25832").to_crs("EPSG:4326"))

    return bbox_matrix




if __name__ == "__main__":
    import os
    print(os.getcwd())

    buildings = gpd.read_file("/home/andre/COUP/code/CUT-prototype-wind-api-v2/infrared_wrapper_api/models/jsons/__all__buildings.json")



    create_bbox_matrix(buildings)