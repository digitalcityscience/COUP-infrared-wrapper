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
def find_idle_infrared_project(all_project_keys) -> str:
    for project_key in all_project_keys:
        project_status: ProjectStatus = cache.get(key=project_key)
        print(project_status)
        if not project_status or not project_status["is_busy"]:
            update_infrared_project_status_in_redis(project_uuid=project_key, is_busy=True)
            print(f" using infrared project {project_key}")
            return project_key

    raise NoIdleProjectException("All infrared projects seem to be in use!")


def update_infrared_project_status_in_redis(project_uuid: str, is_busy: bool):
    """
    marks whether a infrared project can be used or is busy with some other simulation
    """
    cache.put(key=project_uuid, value={"is_busy": is_busy})


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
