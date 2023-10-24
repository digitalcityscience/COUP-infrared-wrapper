import hashlib
import json
import logging
from enum import Enum

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_project_for_user
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


def find_idle_infrared_project(infrared_user_json: dict) -> str:

    """
    TODO wait for project to become available if none.
    TODO should probably be a function  in the user file!
    TODO or better to be in utils??
    """
    all_project_keys = get_all_project_for_user(infrared_user_json["uuid"], infrared_user_json["token"]).keys()

    for project_key in all_project_keys:
        project_status: ProjectStatus = cache.get(key=project_key)
        if project_status or not project_status.is_busy:
            return project_key