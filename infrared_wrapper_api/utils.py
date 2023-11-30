import hashlib
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus, SimType
from infrared_wrapper_api.dependencies import cache

logger = logging.getLogger(__name__)


class NoIdleProjectException(Exception):
    "Raised when no idle project found"
    pass


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


def update_infrared_project_status_in_redis(project_uuid: str, is_busy: bool):
    """
    marks whether a infrared project can be used or is busy with some other simulation
    """
    cache.put(key=project_uuid, value={"is_busy": is_busy})


def is_cut_prototype_project(project_name: str):
    return project_name.startswith("CUT")


@retry(
    stop=stop_after_attempt(5),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=30),  # Exponential backoff with a maximum wait time of 20 seconds
    retry=retry_if_exception_type(NoIdleProjectException)  # Retry only on APIError exceptions
)
def find_idle_infrared_project(all_project_keys) -> str:
    for project_key in all_project_keys:
        project_status: ProjectStatus = cache.get(key=project_key)
        print(project_status)
        if not project_status or not project_status["is_busy"]:
            update_infrared_project_status_in_redis(project_uuid=project_key, is_busy=True)
            print(f" using infrared project {project_key}")
            return project_key

    raise NoIdleProjectException("All infrared projects seem to be in use!")
