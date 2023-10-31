import os
import json
import pytest
from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_building_uuids_for_project, \
    InfraredConnector
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis


@pytest.fixture
def sample_building_data():
    print(os.getcwd())
    with open("../../models/jsons/buildings.json", "r") as f:
        return json.load(f)


@pytest.fixture
def sample_simulation_area():
    print(os.getcwd())
    with open("../../models/jsons/simulation_area.json", "r") as f:
        return json.load(f)


def get_idle_project_id():
    # Mock functions
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        return find_idle_infrared_project()


def test_login():
    connector = InfraredConnector()
    connector.infrared_user_login()

    assert connector.token is not None
    assert connector.user_uuid is not None


def test_getting_idle_project():
    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        project_uuid = find_idle_infrared_project()

        # Assertions
        mocK_cache_get.assert_called()
        mock_update_status.assert_called_once_with(project_uuid=project_uuid, is_busy=True)
        assert project_uuid is not None


def test_create_infrared_project():
    # create buildings at infrared
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)

    assert project.snapshot_uuid is not None


def test_update_and_delete_buildings_at_infrared(sample_building_data, sample_simulation_area):
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)
    project.update_buildings_at_infrared(sample_building_data, sample_simulation_area)

    # Assertions
    building_count = len(sample_building_data["features"])
    assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == building_count

    # Delete the buildings again
    project = InfraredProject(project_uuid)
    project.delete_all_buildings()
    assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == 0


def test_set_project_busy_status_false():
    project_uuid = get_idle_project_id()

    with patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        # set project as not busy.
        update_infrared_project_status_in_redis(project_uuid, False)
        mock_cache_put.assert_called_once_with(key=project_uuid, value={'is_busy': False})



# TODO test triggerin simulation and fetching result.