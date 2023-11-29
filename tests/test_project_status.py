from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from tests.utils import get_idle_project_id


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
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        project_uuid = find_idle_infrared_project(get_all_cut_prototype_projects_uuids())

        # Assertions
        mocK_cache_get.assert_called()
        mock_update_status.assert_called_once_with(project_uuid=project_uuid, is_busy=True)
        assert project_uuid is not None


def test_set_project_busy_status_false():
    """
    Tests the update of a project status
    """
    project_uuid = get_idle_project_id()

    with patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        # set project as not busy.
        update_infrared_project_status_in_redis(project_uuid, False)
        mock_cache_put.assert_called_once_with(key=project_uuid, value={'is_busy': False})
