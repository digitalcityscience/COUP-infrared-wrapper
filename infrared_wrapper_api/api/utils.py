from celery.result import GroupResult
import geopandas as gpd
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.dependencies import cache


class NoIdleProjectException(Exception):
    "Raised when no idle project found"
    pass


@retry(
    stop=stop_after_attempt(5),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=30),  # Exponential backoff with a maximum wait time of 20 seconds
    retry=retry_if_exception_type(NoIdleProjectException)  # Retry only on APIError exceptions
)
def find_idle_infrared_project(all_project_uuids) -> str:
    for project_uuid in all_project_uuids:
        project_info = cache.get(key=project_uuid)
        print(f"project info: {project_info}")
        if not project_info or project_info.get("status", None) == ProjectStatus.IDLE.value:
            update_infrared_project_status_in_redis(project_uuid=project_uuid, status=ProjectStatus.BUSY.value)
            print(f" using infrared project {project_uuid}")
            return project_uuid

    raise NoIdleProjectException("All infrared projects seem to be in use!")


def update_infrared_project_status_in_redis(project_uuid: str, status: str):
    """
    marks whether a infrared project can be used or is busy with some other simulation
    """
    cache.put(key=project_uuid, value={"status": status})


def unify_group_result(group_result: GroupResult) -> dict:
    # list of geojsons
    all_results = [result.get() for result in group_result.results]

    # flatten all features to one list
    all_features = []
    for result in all_results:
        all_features.extend(result.get("features", []))

    # dissolve neighboring polygons with same value
    gdf = gpd.GeoDataFrame.from_features(all_features)
    gdf = gdf.dissolve(by='value').reset_index()

    return json.loads(gdf.to_json())
