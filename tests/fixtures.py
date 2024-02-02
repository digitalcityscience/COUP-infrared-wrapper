import json
import os
import pytest

from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson


@pytest.fixture
def sample_simulation_area():
    print(os.getcwd())
    with open("../infrared_wrapper_api/models/jsons/simulation_area.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_simulation_result_raw():
    print(os.getcwd())
    with open("../infrared_wrapper_api/models/jsons/infrared_result_raw.json", "r") as f:
        return json.load(f)


@pytest.fixture
def sample_simulation_result_single_bbox_geojson():
    print(os.getcwd())
    with open("../infrared_wrapper_api/models/jsons/infrared_result_single_bbox.geojson", "r") as f:
        return json.load(f)

# @pytest.fixture
# def sample_all_building_data():
#     """
#     for local tests with extended buildings only
#     """
#     print(os.getcwd())
#     with open("../infrared_wrapper_api/models/jsons/__all__buildings.json", "r") as f:
#         geojson = json.load(f)
#         return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")

@pytest.fixture
def sample_building_data_multiple_bbox():
    print(os.getcwd())
    with open("../infrared_wrapper_api/models/jsons/buildings_multiple_bboxes.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_building_data_single_bbox():
    print(os.getcwd())
    with open("../infrared_wrapper_api/models/jsons/buildings_single_bbox.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_simulation_input(sample_building_data_single_bbox):
    return {
        "buildings": sample_building_data_single_bbox,
        "wind_speed": 10,
        "wind_direction": 45,
    }

@pytest.fixture
def sample_simulation_input_multiple_bboxes(sample_building_data_multiple_bbox):
    return {
        "buildings": sample_building_data_multiple_bbox,
        "wind_speed": 10,
        "wind_direction": 45,
    }


