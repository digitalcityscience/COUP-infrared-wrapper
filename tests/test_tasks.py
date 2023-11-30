import pytest
import geopandas as gpd
from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks, create_bbox_matrix
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.tasks import task__do_simulation
from tests.fixtures import sample_simulation_input, sample_simulation_area, sample_building_data


def test_create_bbox_matrix(sample_building_data):
    bbox_matrix = create_bbox_matrix(
        gpd.GeoDataFrame.from_features(sample_building_data["features"], crs="EPSG:4326"))
    test_bbox = bbox_matrix[0]

    assert type(test_bbox) == gpd.GeoDataFrame

    # test bbox size
    minx, miny, maxx, maxy = test_bbox.total_bounds

    assert pytest.approx(maxx - minx) == settings.infrared_calculation.infrared_sim_area_size
    assert pytest.approx(maxy - miny) == settings.infrared_calculation.infrared_sim_area_size


def test_create_simulation_tasks(sample_simulation_input):
    sim_tasks = create_simulation_tasks(sample_simulation_input, "wind")

    for test_sim_task in sim_tasks:
        assert type(test_sim_task) == WindSimulationTask
        assert len(test_sim_task.buildings["features"]) > 0

        # test building in bbox
        sim_area_gdf = gpd.GeoDataFrame.from_features(test_sim_task.simulation_area["features"])
        buildings_gdf = gpd.GeoDataFrame.from_features(test_sim_task.buildings["features"])

        assert buildings_gdf.intersects(sim_area_gdf.unary_union.convex_hull).all()


def test_task_not_cached(sample_simulation_area, sample_building_data):
    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.tasks.cache.get", return_value=None) as mock_cache_get, \
            patch("infrared_wrapper_api.tasks.do_simulation") as mock_do_sim:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = WindSimulationTask(
            simulation_area=sample_simulation_area,
            buildings=sample_building_data,
            wind_speed=15,
            wind_direction=15
        )

        task__do_simulation(mock_project_uuid, sample_wind_sim_task.dict())

        # Assert checking in cache
        mock_cache_get.assert_called()
        mock_cache_get.assert_called_once_with(key=sample_wind_sim_task.celery_key)
        # Assert wind simulation is called, as result of task is not cached
        mock_do_sim.assert_called_once_with(project_uuid=mock_project_uuid, sim_task=sample_wind_sim_task.dict())


def test_task_is_cached(sample_simulation_area, sample_building_data):
    # Mock functions that require a redis instance to run.
    mock_result = {"result": "placeholder"}
    with patch("infrared_wrapper_api.tasks.cache.get", return_value=mock_result) as mock_cache_get, \
            patch("infrared_wrapper_api.infrared_wrapper.infrared.simulation.do_simulation") as mock_do_sim:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = WindSimulationTask(
            simulation_area=sample_simulation_area,
            buildings=sample_building_data,
            wind_speed=15,
            wind_direction=15
        )
        result = task__do_simulation(mock_project_uuid, sample_wind_sim_task.dict())

        # Assert checking in cache
        mock_cache_get.assert_called()
        # Assert wind simulation is NOT called, as we found result of task in cache
        mock_do_sim.assert_not_called()

        # Asser returned result is the mock result
        assert result == mock_result
