import pytest
import json
import geopandas as gpd
import os

from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks, create_bbox_matrix
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_wind_simulation
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.utils import find_idle_infrared_project


@pytest.fixture
def sample_building_data():
    print(os.getcwd())
    with open("./models/jsons/__all__buildings.json", "r") as f:
        return json.load(f)


@pytest.fixture
def sample_task_def(sample_building_data):
    return {
        "buildings": sample_building_data,
        "wind_speed": 10,
        "wind_direction": 45,
    }


def test_create_bbox_matrix(sample_building_data):
    bbox_matrix = create_bbox_matrix(gpd.GeoDataFrame.from_features(sample_building_data["features"], crs="EPSG:4326"))
    test_bbox = bbox_matrix[0]

    assert type(test_bbox) == gpd.GeoDataFrame

    # test bbox size
    test_bbox = test_bbox.to_crs("EPSG:25832")
    minx, miny, maxx, maxy = test_bbox.total_bounds

    assert pytest.approx(maxx - minx) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer
    assert pytest.approx(maxy - miny) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer


def test_create_simulation_tasks(sample_task_def, sample_building_data):
    sim_tasks = create_simulation_tasks(sample_task_def)

    for test_sim_task in sim_tasks:
        assert type(test_sim_task) == WindSimulationTask
        assert len(test_sim_task.buildings["features"]) > 0

        # test building in bbox
        sim_area_gdf = gpd.GeoDataFrame.from_features(test_sim_task.simulation_area["features"])
        buildings_gdf = gpd.GeoDataFrame.from_features(test_sim_task.buildings["features"])

        assert buildings_gdf.intersects(sim_area_gdf.unary_union.convex_hull).all()


def test_do_wind_simulation(sample_task_def):

    project_uuid = find_idle_infrared_project()
    sim_tasks = create_simulation_tasks(sample_task_def)
    test_sim_task = sim_tasks[0]

    do_wind_simulation(project_uuid, test_sim_task)



    #    "query": "mutation {\n        createNewBuilding (\n          use: \"residential\"\n          height: 3\n          category: \"site\"          \n          geometry: \"{\\\"type\\\": \\\"Polygon\\\", \\\"coordinates\\\":[[[213.37471,111.012283],[209.514862,69.0545654],[152.85437,64.77655],[154.43808,138.8753],[244.306641,198.100037],[179.040955,110.922424],[213.37471,111.012283]]]}\"\n          snapshotUuid: \"d781223c-d46c-4f6c-b0c9-d08beee803e2\"\n        ){\n          success\n          uuid\n        }      \n      }"}
