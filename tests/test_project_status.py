from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.tasks import task__do_simulation
from tests.utils import get_idle_project_id
from tests.fixtures import sample_simulation_area, sample_building_data_single_bbox


def test_update_project_status():
    """
    Tests the update of a project status
    """
    project_uuid = get_idle_project_id()

    with patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        # set project as idle.
        update_infrared_project_status_in_redis(project_uuid, ProjectStatus.IDLE.value)
        mock_cache_put.assert_called_once_with(key=project_uuid, value={"status": ProjectStatus.IDLE.value})


def test_getting_idle_project():
    """
    Test the communication with redis, when choosing an infrared project that is idle.
    We are documenting the project state (busy, not busy) in the redis db on our side,
    in order to avoid using the same InfraredProject by 2 simultaneous requests

    This test
    - should check if the project is busy
    - selected project should be marked as busy upon selection
    """

    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch(
                "infrared_wrapper_api.dependencies.cache.get",
                return_value={"status": ProjectStatus.IDLE.value}
            ) as mocK_cache_get:
        project_uuid = find_idle_infrared_project(get_all_cut_prototype_projects_uuids())

        # Assert that selected project will be marked busy.
        mocK_cache_get.assert_called()
        mock_update_status.assert_called_once_with(project_uuid=project_uuid, status=ProjectStatus.BUSY.value)
        assert project_uuid is not None


def test_mark_completed_after_simulation(sample_simulation_area, sample_building_data_single_bbox):
    """
    This test
    - mocks a simulation task is being executed.
    - tests if the infrared project is marked "completed" at the end of the simulation
    """

    mock_result = {"features": [{"id": "test"}]}

    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.tasks.cache.get", return_value={}) as mock_cache_get, \
            patch("infrared_wrapper_api.tasks.do_simulation", return_value=mock_result) as mock_do_sim, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        mock_project_uuid = "abc123"
        sample_wind_sim_task = WindSimulationTask(
            simulation_area=sample_simulation_area,
            buildings=sample_building_data_single_bbox,
            wind_speed=15,
            wind_direction=15
        )
        result = task__do_simulation(mock_project_uuid, sample_wind_sim_task.dict())

        # Assert that selected project will be marked busy.
        mock_cache_get.assert_called()
        mock_do_sim.assert_called()
        mock_cache_put.assert_called_with(key=mock_project_uuid, value={"status": ProjectStatus.TO_BE_CLEANED.value})
