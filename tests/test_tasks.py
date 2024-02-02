import json

import pytest
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

from unittest.mock import patch

from infrared_wrapper_api.api.utils import find_idle_infrared_project
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks, create_bbox_matrix
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.infrared_wrapper.infrared.setup.setup_infrared import cleanup_project
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_simulation
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.tasks import task__do_simulation
from tests.fixtures import sample_simulation_input, sample_simulation_area, sample_building_data_multiple_bbox, \
    sample_building_data_single_bbox, sample_simulation_result_single_bbox_geojson, sample_simulation_input_multiple_bboxes


def test_create_bbox_matrix_multiple_bbox(sample_building_data_multiple_bbox):
    bbox_matrix = create_bbox_matrix(
        gpd.GeoDataFrame.from_features(sample_building_data_multiple_bbox["features"], crs="EPSG:25832"))
    test_bbox = bbox_matrix[0]

    # combine all bbox_matrix into 1 gdf
    bboxes_gdf = pd.concat(bbox_gdf for bbox_gdf in bbox_matrix)

    buildings_gdf = gpd.GeoDataFrame.from_features(sample_building_data_multiple_bbox["features"], crs="EPSG:25832")

    f, ax = plt.subplots()
    bboxes_gdf.plot(ax=ax, facecolor="none",
                    lw=0.7, cmap='Set1')
    buildings_gdf.plot(ax=ax)

    print("length of bbox matrix", len(bbox_matrix))

    plt.show()

    assert type(test_bbox) == gpd.GeoDataFrame

    # test bbox size
    minx, miny, maxx, maxy = test_bbox.total_bounds

    assert pytest.approx(maxx - minx) == settings.infrared_calculation.infrared_sim_area_size
    assert pytest.approx(maxy - miny) == settings.infrared_calculation.infrared_sim_area_size


def test_create_bbox_matrix_single_bbox(sample_building_data_single_bbox):
    bbox_matrix = create_bbox_matrix(
        gpd.GeoDataFrame.from_features(sample_building_data_single_bbox["features"], crs="EPSG:4326")
    )
    # combine all bbox_matrix into 1 gdf
    bboxes_gdf = pd.concat(bbox_gdf for bbox_gdf in bbox_matrix)
    f, ax = plt.subplots()
    bboxes_gdf.plot(ax=ax, facecolor="none",
                    lw=0.7, cmap='Set1')

    buildings_gdf = gpd.GeoDataFrame.from_features(sample_building_data_single_bbox["features"], crs="EPSG:25832")
    buildings_gdf.plot(ax=ax)

    plt.show()

    # assert single bbox
    assert 1 == len(bbox_matrix)
    # assert bbox has same bounds as buildings
    assert set(list(bbox_matrix[0].total_bounds)) == set(list(buildings_gdf.total_bounds))


def test_create_simulation_tasks(sample_simulation_input):
    sim_tasks = create_simulation_tasks(sample_simulation_input, "wind")

    for test_sim_task in sim_tasks:
        assert type(test_sim_task) == WindSimulationTask
        assert len(test_sim_task.buildings["features"]) > 0

        # test building in bbox
        sim_area_gdf = gpd.GeoDataFrame.from_features(test_sim_task.simulation_area["features"])
        buildings_gdf = gpd.GeoDataFrame.from_features(test_sim_task.buildings["features"])

        assert buildings_gdf.intersects(sim_area_gdf.unary_union.convex_hull).all()


def test_task_not_cached(sample_simulation_area, sample_building_data_single_bbox):
    # Mock functions that require a redis instance to run.
    mock_result = {"features": [{"id": "test"}]}
    with patch(
            "infrared_wrapper_api.tasks.do_simulation",
            return_value=mock_result
    ) as mock_do_sim, \
            patch("infrared_wrapper_api.tasks.cache.get", return_value={}) as mock_cache_get, \
            patch("infrared_wrapper_api.tasks.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.tasks.cache.put") as mock_cache_put:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = WindSimulationTask(
            simulation_area=sample_simulation_area,
            buildings=sample_building_data_single_bbox,
            wind_speed=15,
            wind_direction=15
        )

        result = task__do_simulation(mock_project_uuid, sample_wind_sim_task.dict())

        # Assert checking in cache
        mock_cache_get.assert_called()
        mock_cache_get.assert_called_once_with(key=sample_wind_sim_task.celery_key)
        # Assert wind simulation is called, as result of task is not cached
        mock_do_sim.assert_called_once_with(project_uuid=mock_project_uuid, sim_task=sample_wind_sim_task.dict())
        assert result == mock_result

        mock_update_status.assert_called()

        # Assert caching of result
        mock_cache_put.assert_called()
        mock_cache_put.assert_called_with(key=sample_wind_sim_task.celery_key, value=mock_result)


def test_task_is_cached(sample_simulation_area, sample_building_data_single_bbox):
    # Mock functions that require a redis instance to run.
    mock_result_from_cache = {"features": [{"id": "test"}]}
    with patch("infrared_wrapper_api.tasks.cache.get", return_value=mock_result_from_cache) as mock_cache_get, \
            patch("infrared_wrapper_api.tasks.do_simulation") as mock_do_sim:
        # call function
        mock_project_uuid = "abc123"
        sample_wind_sim_task = WindSimulationTask(
            simulation_area=sample_simulation_area,
            buildings=sample_building_data_single_bbox,
            wind_speed=15,
            wind_direction=15
        )
        result = task__do_simulation(mock_project_uuid, sample_wind_sim_task.dict())

        # Assert checking in cache
        mock_cache_get.assert_called()
        # Assert wind simulation is NOT called, as we found result of task in cache
        mock_do_sim.assert_not_called()

        # Asser returned result is the mock result
        assert result == mock_result_from_cache


def test_simulation_result_single_bbox(sample_simulation_input, sample_simulation_result_single_bbox_geojson):
    # TODO SET TO TRUE TO RUN TEST
    run_test_that_costs_infrared_tokens = True

    if not run_test_that_costs_infrared_tokens:
        pytest.skip("Skipping test_simulation_result_single_bbox")

    """
    Tests real INFRARED Simulation and compares result to known result.
    """
    import time
    start_time = time.time()


    simulation_tasks = create_simulation_tasks(sample_simulation_input, "wind")
    assert len(simulation_tasks) == 1

    with patch(
            "infrared_wrapper_api.dependencies.cache.get",
            return_value={"status": ProjectStatus.IDLE.value}
    ) as mock_cache_get, \
        patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        project_uuid = find_idle_infrared_project(get_all_cut_prototype_projects_uuids())

        print("running simulation on Infrared project {}".format(project_uuid))

        result = do_simulation(
            project_uuid=project_uuid,
            sim_task=simulation_tasks[0].dict()
        )

        print("SIMULATION TIME TOOK {:.2f} seconds".format(time.time() - start_time))

        with open("single_bbox_sim_result_2.json", "w") as f:
            json.dump(result, f)

        assert result == sample_simulation_result_single_bbox_geojson

        # dont forget to clean up project_uuid
        cleanup_project(project_uuid)


def test_simulation_result_multiple_bbox(sample_simulation_input_multiple_bboxes):
    # TODO SET TO TRUE TO RUN TEST
    run_test_that_costs_infrared_tokens = True
    if not run_test_that_costs_infrared_tokens:
        pytest.skip("Skipping test_simulation_result_multiple_bbox")


    """
    Tests real INFRARED Simulation and compares result to known result.
    """
    import time
    import random

    simulation_tasks = create_simulation_tasks(sample_simulation_input_multiple_bboxes, "wind")
    # TODO hier stehen irgendwie multipolygons in den buildings. WO auch immer die herkommen: explode!

    assert len(simulation_tasks) == 4

    all_project_uuids = get_all_cut_prototype_projects_uuids()
    sample_size = len(simulation_tasks)

    test_uuids = random.sample(all_project_uuids, sample_size)

    with patch(
            "infrared_wrapper_api.dependencies.cache.get",
            return_value={"status": ProjectStatus.IDLE.value}
    ) as mock_cache_get, \
        patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:

        try:
            for sim_task_id, simulation_task in enumerate(simulation_tasks):
                start_time = time.time()

                print("running simulation on Infrared project {}".format(test_uuids[sim_task_id]))

                with open(f"sim_task{sim_task_id}.json", "w") as f:
                    json.dump(simulation_task.dict(), f)

                result = do_simulation(
                    project_uuid=test_uuids[sim_task_id],
                    sim_task=simulation_task.dict()
                )

                print("SIMULATION TIME TOOK {:.2f} seconds".format(time.time() - start_time))

                with open(f"multiple_bbox_sim_result_{sim_task_id}", "w") as f:
                    json.dump(result, f)

                ## TODO assert results
                ##assert result == sample_simulation_result_single_bbox_geojson
        except Exception as e:
            print(f"Something went wrong {e}")

        finally:
            for uuid in test_uuids:
                try:
                    cleanup_project(uuid)
                except:
                    print("cannot clean up project {}".format(uuid))
