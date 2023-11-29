from unittest.mock import patch

from infrared_wrapper_api.utils import find_idle_infrared_project
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids


def get_idle_project_id():
    # Mock functions so that the projects are not marked busy!
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        return find_idle_infrared_project(get_all_cut_prototype_projects_uuids())

