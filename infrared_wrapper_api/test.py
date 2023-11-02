import pytest
import json
import geopandas as gpd
import os
from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks, create_bbox_matrix
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.tasks import task_do_wind_simulation


@pytest.fixture
def sample_all_building_data():
    print(os.getcwd())
    with open("./models/jsons/__all__buildings.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_simulation_input(sample_all_building_data):
    return {
        "buildings": sample_all_building_data,
        "wind_speed": 10,
        "wind_direction": 45,
    }


@pytest.fixture
def sample_simulation_area():
    print(os.getcwd())
    with open("./models/jsons/simulation_area.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_single_task_building_data():
    print(os.getcwd())
    with open("./models/jsons/buildings.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


#
# @pytest.fixture
# def sample_wind_sim_task(sample_all_building_data):
#     return {
#         "buildings": sample_single_task_building_data,
#         "simulation_area": sample_simulation_area,
#         "wind_speed": 10,
#         "wind_direction": 45,
#     }


def test_create_bbox_matrix(sample_all_building_data):
    bbox_matrix = create_bbox_matrix(
        gpd.GeoDataFrame.from_features(sample_all_building_data["features"], crs="EPSG:4326"))
    test_bbox = bbox_matrix[0]

    assert type(test_bbox) == gpd.GeoDataFrame

    # test bbox size
    minx, miny, maxx, maxy = test_bbox.total_bounds

    assert pytest.approx(maxx - minx) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer
    assert pytest.approx(maxy - miny) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer


def test_create_simulation_tasks(sample_simulation_input, sample_all_building_data):
    sim_tasks = create_simulation_tasks(sample_simulation_input)

    for test_sim_task in sim_tasks:
        assert type(test_sim_task) == WindSimulationTask
        assert len(test_sim_task.buildings["features"]) > 0

        # test building in bbox
        sim_area_gdf = gpd.GeoDataFrame.from_features(test_sim_task.simulation_area["features"])
        buildings_gdf = gpd.GeoDataFrame.from_features(test_sim_task.buildings["features"])

        assert buildings_gdf.intersects(sim_area_gdf.unary_union.convex_hull).all()


def test_task_not_cached(sample_simulation_area, sample_single_task_building_data):
    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.dependencies.cache.get", return_value=None) as mock_cache_get, \
            patch(
                "infrared_wrapper_api.tasks.do_wind_simulation",
                ) as mock_do_wind_sim:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = {
            "simulation_area": sample_simulation_area,
            "buildings": sample_single_task_building_data,
            "wind_speed": 15,
            "wind_direction": 15
        }

        task_do_wind_simulation(mock_project_uuid, sample_wind_sim_task)

        # Assert checking in cache
        mock_cache_get.assert_called()
        task = WindSimulationTask(**sample_wind_sim_task)
        mock_cache_get.assert_called_once_with(key=task.celery_key)
        # Assert wind simulation is called, as result of task is not cached
        mock_do_wind_sim.assert_called_once_with(project_uuid=mock_project_uuid, wind_sim_task=sample_wind_sim_task)


def test_task_is_cached(sample_simulation_area, sample_single_task_building_data):
    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.dependencies.cache.get", return_value={"result": "placeholder"}) as mock_cache_get, \
            patch("infrared_wrapper_api.infrared_wrapper.infrared.simulation.do_wind_simulation") as mock_do_wind_sim:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = {
            "simulation_area": sample_simulation_area,
            "buildings": sample_single_task_building_data,
            "wind_speed": 15,
            "wind_direction": 15
        }
        task_do_wind_simulation(mock_project_uuid, sample_wind_sim_task)

        # Assert checking in cache
        mock_cache_get.assert_called()
        # Assert wind simulation is NOT called, as we found result of task in cache
        mock_do_wind_sim.assert_not_called()
