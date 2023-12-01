import hashlib
import json
import logging

from infrared_wrapper_api.infrared_wrapper.infrared.models import  SimType
from infrared_wrapper_api.dependencies import cache

logger = logging.getLogger(__name__)

def hash_dict(dict_) -> str:
    dict_str = json.dumps(dict_, sort_keys=True)
    return hashlib.md5(dict_str.encode()).hexdigest()


def load_json_file(path: str) -> dict:
    with open(path, "r") as f:
        return json.loads(f.read())


def log_request(sim_type: SimType):
    
    if current_count := cache.get(key=f"sim_requests_{sim_type}") is None:
        current_count = 0

    cache.put(
        key=f"sim_requests_{sim_type}",
        value=current_count + 1
    )


def get_request_log_count(sim_type: SimType):
    return cache.get(key=f"sim_requests_{sim_type}")


def is_cut_prototype_project(project_name: str):
    return project_name.startswith("CUT")


