import hashlib
import json
import logging
from enum import Enum
from typing import List

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_projects_for_user
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.dependencies import cache

logger = logging.getLogger(__name__)


def hash_dict(dict_) -> str:
    dict_str = json.dumps(dict_, sort_keys=True)
    return hashlib.md5(dict_str.encode()).hexdigest()


def enum_to_list(enum_class: Enum) -> list[str]:
    return [member.value for member in enum_class]


def load_json_file(path: str) -> dict:
    with open(path, "r") as f:
        return json.loads(f.read())


def update_infrared_project_status_in_redis(project_uuid: str, is_busy:bool):
    """
    marks whether a infrared project can be used or is busy with some other simulation
    """
    cache.put(key=project_uuid, value={"is_busy": is_busy})


def get_all_infrared_project_uuids() -> List[str]:
    if uuids := get_all_projects_for_user().keys():
        return uuids
    else:
        raise ValueError("No projects exist at infrared endpoint")


def find_idle_infrared_project(all_project_keys) -> str:

    """
    TODO wait for project to become available if none.
    TODO should probably be a function  in the user file!
    TODO or better to be in utils??
    """
    for project_key in all_project_keys:
        project_status: ProjectStatus = cache.get(key=project_key)
        print(project_status)
        if not project_status or not project_status["is_busy"]:
            update_infrared_project_status_in_redis(project_uuid=project_key, is_busy=True)
            print(f" using infrared project {project_key}")
            return project_key

    # TODO wait until is is idle. with luis retry method?
    raise NotImplementedError("implement waiting for idle projects")



if __name__ == "__main__":
    print("setting all projects to not busy")

    all_project_keys = get_all_projects_for_user().keys()
    print(f"all project keys {all_project_keys}")

    if not all_project_keys:
        raise ValueError("No projects exist at infrared endpoint")

    for project_key in all_project_keys:
        project_status: ProjectStatus = cache.get(key=project_key)
        print(project_status)
        update_infrared_project_status_in_redis(project_uuid=project_key, is_busy=False)
        print(f" set not busy infrared project {project_key}")