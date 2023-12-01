import os
import requests
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from infrared_wrapper_api.infrared_wrapper.infrared import queries
from infrared_wrapper_api.infrared_wrapper.infrared.queries import run_wind_simulation_query, get_analysis_output_query, \
    run_sunlight_hours_service_query, activate_sun_service_query
from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.utils import is_cut_prototype_project


class InfraredException(Exception):
    "Raised when no idle project found"
    pass


class InfraredConnector:

    def __init__(self):
        self.user_uuid = ""
        self.token = ""
        self.infrared_user_login()

    def infrared_user_login(self) -> tuple[str]:
        user_creds = {
            "username": settings.infrared_communication.user,
            "password": settings.infrared_communication.password
        }
        request = requests.post(os.getenv("INFRARED_URL"), json=user_creds)

        if request.status_code != 200:
            raise Exception(
                f"Failed to login to infrared by returning code of {request.status_code}"
            )
        else:
            print("LOGIN TO INFRARED SUCCESSFUL")
        # get the auth token from the returned cookie
        print(request.cookies)

        self.user_uuid = request.cookies.get("InFraReDClientUuid")
        self.token = "InFraReD=" + request.cookies.get("InFraReD")

    def execute_query(self, query: str):
        """
            Make query response
            auth token needs to be sent as cookie
        """
        start_time = time.time()

        # AIT requested a sleep between the requests. To let their servers breath a bit.
        url = os.getenv("INFRARED_URL") + '/api'
        headers = {'Cookie': self.token, 'origin': os.getenv('INFRARED_URL')}
        request = requests.post(url, json={'query': query}, headers=headers)

        if request.status_code == 401:
            # cookies expire after 1hour - reauthenticate and try again
            print("COOKIE EXPIRED - LOGGING IN AGAIN")
            self.infrared_user_login()
            return self.execute_query(query)

        if request.status_code != 200:
            raise InfraredException(
                f"Query failed to run by returning code of {request.status_code}. URL: {url} , Query: {query}, Headers: {headers}"
            )
        print(f"Query: {query.split('(')[0]} ||| execution time: {time.time() - start_time}")
        return request.json()


connector = InfraredConnector()


"""
PROJECT CREATION / DELETION / IDS
"""

@retry(
    stop=stop_after_attempt(5),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=20),  # Exponential backoff with a maximum wait time of 10 seconds
    retry=retry_if_exception_type(InfraredException)  # Retry only on APIError exceptions
)
def create_new_project(name):
    query = queries.create_project_query(
        user_uuid=connector.user_uuid,
        name=name,
        sw_lat=53.5488,
        sw_long=9.9872,
        bbox_size=settings.infrared_calculation.infrared_sim_area_size,
        resolution=settings.infrared_calculation.analysis_resolution
    )
    new_project_response = connector.execute_query(query)

    if not new_project_response["data"]["createNewProject"]["success"]:
        raise InfraredException("could not create new project")

    return get_value(
        new_project_response, ["data", "createNewProject", "uuid"]
    )


def get_all_cut_prototype_projects_uuids() -> List[str]:
    query = queries.get_projects_query(connector.user_uuid)

    try:
        all_projects = get_value(
            connector.execute_query(query),
            ["data", "getProjectsByUserUuid", "infraredSchema", "clients", connector.user_uuid, "projects"]
        )
    except KeyError:
        print("no projects for user")
        return []

    return [
        uuid
        for uuid in all_projects.keys()
        if is_cut_prototype_project(all_projects[uuid]["projectName"])
    ]


def get_root_snapshot_id(project_uuid) -> str:
    query = queries.get_snapshot_query(project_uuid)

    snapshot = connector.execute_query(query)
    graph_snapshots_path = ["data", "getSnapshotsByProjectUuid", "infraredSchema", "clients", connector.user_uuid,
                            "projects", project_uuid, "snapshots"]

    return list(get_value(snapshot, graph_snapshots_path).keys())[0]  # root snapshot is the first (and only) one.
    # the root snapshot of the infrared project will be used to create buildings and perform analysis


def get_project_name(project_uuid) -> str:
    query = queries.get_snapshot_query(project_uuid)

    snapshot = connector.execute_query(query)
    name_path = ["data", "getSnapshotsByProjectUuid", "infraredSchema", "clients", connector.user_uuid,
                            "projects", project_uuid, "projectName"]

    return get_value(snapshot, name_path)


"""
BUILDINGS AND STREETS
"""


@retry(
    stop=stop_after_attempt(5),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=20),  # Exponential backoff with a maximum wait time of 10 seconds
    retry=retry_if_exception_type(InfraredException)  # Retry only on APIError exceptions
)
def create_new_buildings(snapshot_uuid: str, new_buildings: dict):
    query = queries.create_buildings(snapshot_uuid, new_buildings["features"])
    new_bld_response = connector.execute_query(query)

    all_success = all(entry.get("success", False) for entry in new_bld_response["data"].values())

    if not all_success:
        print(
            f"could not create buildings! {new_bld_response}",
        )
        print(f"Query {query}")


def get_all_project_geometry_objects(project_uuid: str, snapshot_uuid: str) -> dict:
    snapshot_geometries = connector.execute_query(
        queries.get_geometry_objects_in_snapshot_query(snapshot_uuid)
    )

    geometries_path = [
        "data",
        "getSnapshotGeometryObjects",
        "infraredSchema",
        "clients",
        connector.user_uuid,
        "projects",
        project_uuid,
        "snapshots",
        snapshot_uuid,
    ]
    try:
        return get_value(snapshot_geometries, geometries_path)
    except Exception:
        print(f"could not get buildings for project uuid {project_uuid}")
        return {}


def get_all_building_uuids_for_project(project_uuid: str, snapshot_uuid: str) -> List[str]:
    all_geometries = get_all_project_geometry_objects(project_uuid, snapshot_uuid)

    try:
        return all_geometries["buildings"].keys()
    except Exception:
        print(f"could not get buildings for project uuid {project_uuid}")
        return []


def get_all_street_uuids_for_project(project_uuid: str, snapshot_uuid: str) -> List[str]:
    all_geometries = get_all_project_geometry_objects(project_uuid, snapshot_uuid)

    try:
        return all_geometries["streets"].keys()
    except Exception:
        print(f"could not get streets for project uuid {project_uuid}")
        return []


def delete_buildings(snapshot_uuid: str, building_uuids: List[str]):
    response = connector.execute_query(
        queries.delete_buildings(snapshot_uuid, building_uuids)
    )

    all_success = all(entry.get("success", False) for entry in response["data"].values())

    if not all_success:
        print(f"COULD NOT DELETE ALL BUILDINGS {response.json()}")


def delete_streets(snapshot_uuid: str, streets_uuids: List[str]):
    response = connector.execute_query(
        queries.delete_streets(snapshot_uuid, streets_uuids)
    )

    all_success = all(entry.get("success", False) for entry in response["data"].values())

    if not all_success:
        print(f"COULD NOT DELETE ALL STREETS {response.json()}")


"""
SIMULATIONS
"""


def activate_sunlight_analysis_capability(project_uuid: str):
    query = activate_sun_service_query(
        connector.user_uuid, project_uuid
    )
    response = connector.execute_query(query)
    print("activate sunlight hours calc service", response)


def trigger_wind_simulation(snapshot_uuid, wind_direction, wind_speed) -> str:
    query = run_wind_simulation_query(
        snapshot_uuid=snapshot_uuid,
        wind_direction=wind_direction,
        wind_speed=wind_speed
    )

    try:
        print("TRIGGERING WIND SIM")
        response = connector.execute_query(query)
        return get_value(response, ["data", "runServiceWindComfort", "uuid"])
    except Exception as exception:
        print(f"calculation for wind FAILS! for snapshot {snapshot_uuid} with exception {exception}")


def trigger_sun_simulation(snapshot_uuid) -> str:
    query = run_sunlight_hours_service_query(
        snapshot_uuid=snapshot_uuid
    )

    try:
        print("TRIGGERING SUN SIM")
        response = connector.execute_query(query)
        return get_value(response, ["data", "runServiceSunlightHours", "uuid"])
    except Exception as exception:
        print(f"calculation for SUN FAILS! for snapshot {snapshot_uuid} with exception {exception}")


@retry(
    stop=stop_after_attempt(10),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=20),  # Exponential backoff with a maximum wait time of 10 seconds
    retry=retry_if_exception_type(KeyError)  # Retry only on APIError exceptions
)
def get_analysis_output(project_uuid: str, snapshot_uuid: str, result_uuid: str) -> dict:
    query = get_analysis_output_query(
        snapshot_uuid=snapshot_uuid,
        result_uuid=result_uuid
    )
    response = connector.execute_query(query)

    return get_value(
        response,
        [
            "data",
            "getAnalysisOutput",
            "infraredSchema",
            "clients",
            connector.user_uuid,
            "projects",
            project_uuid,
            "snapshots",
            snapshot_uuid,
            "analysisOutputs",
            result_uuid
        ]
    )
