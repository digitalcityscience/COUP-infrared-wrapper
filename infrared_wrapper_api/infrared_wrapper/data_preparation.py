import math
from typing import List
import json

import geopandas as gpd
from shapely.geometry import box
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.infrared_wrapper.infrared.models import SimType
from infrared_wrapper_api.models.calculation_input import WindSimulationTask, SunSimulationTask


def create_simulation_tasks(
        task_def: dict,
        sim_type: SimType
) -> List[WindSimulationTask | SunSimulationTask]:
    buildings_gdf = gpd.GeoDataFrame.from_features(task_def["buildings"]["features"], crs="EPSG:25832")

    # subdivide the region with all buildings into simulation area sized bboxes
    matrix = create_bbox_matrix(buildings_gdf)

    return [create_simulation_task(task_def, buildings_gdf, bbox, sim_type) for bbox in matrix]


def create_simulation_task(
        task_def: dict,
        buildings_gdf: gpd.GeoDataFrame,
        bbox: box,
        sim_type: SimType
) -> WindSimulationTask | SunSimulationTask:
    columns = list(buildings_gdf.columns)
    buildings_gdf = buildings_gdf.drop(columns=[col for col in columns if not col in ["geometry", "building_height", "index"]])
    buildings_gdf = buildings_gdf.clip(bbox)
    buildings_gdf = simplify_building_input(buildings_gdf)
    buildings_json = json.loads(buildings_gdf.to_json())

    simulation_area_json = json.loads(bbox.to_json())

    if sim_type == "wind":
        return WindSimulationTask(
            simulation_area=simulation_area_json,
            buildings=buildings_json,
            wind_speed=task_def["wind_speed"],
            wind_direction=task_def["wind_direction"],
            # TODO add original calculation area here. and when task finished - clip to it.
        )

    if sim_type == "sun":
        return SunSimulationTask(
            simulation_area=simulation_area_json,
            buildings=buildings_json
        )

    raise NotImplementedError(f"Simulation type {sim_type} not known.")


def create_bbox_matrix(buildings: gpd.GeoDataFrame) -> List[gpd.GeoDataFrame]:
    """
    creates a matrix of overlapping bboxes covering the area containing buildings (EPSG:25832)
    """
    total_area = buildings.unary_union.convex_hull
    min_x, min_y, max_x, max_y = total_area.bounds
    size = settings.infrared_calculation.cropped_simulation_area_size
    buffer = settings.infrared_calculation.simulation_area_buffer

    print("INPUT SIZE BOUNDARIES")
    print(max_x - min_x)
    print(max_y - min_y)

    if max_x - min_x <= 500 >= max_y - min_y:
        # return a single bbox for requests that fit into a single 500*500m bounding box.
        print("Single bbox")
        return [gpd.GeoDataFrame(geometry=[box(min_x, min_y, max_x, max_y)], crs="EPSG:25832")]

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
            _bbox_without_buffer = box(box_min_x + buffer, box_min_y + buffer, box_max_x - buffer, box_max_y - buffer)
            if total_area.intersection(_bbox_without_buffer):
                # only add bbox to matrix, if actually intersecting with the project area polygon
                bbox_matrix.append(gpd.GeoDataFrame(geometry=[bbox], crs="EPSG:25832"))

    return bbox_matrix


def simplify_building_input(buildings_in_bbox: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    buildings_in_bbox["building_height"] = round(buildings_in_bbox["building_height"], -1)  # round to next 10
    buildings_in_bbox["building_height_dissolve"] = buildings_in_bbox["building_height"]
    buildings_in_bbox.geometry = buildings_in_bbox.simplify(tolerance=1)
    buildings_in_bbox = buildings_in_bbox.dissolve(by="building_height_dissolve")

    return buildings_in_bbox


