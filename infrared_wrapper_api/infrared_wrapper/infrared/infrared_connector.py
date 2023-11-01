import os
import requests
import time
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from infrared_wrapper_api.infrared_wrapper.infrared import queries
from infrared_wrapper_api.infrared_wrapper.infrared.queries import run_wind_simulation_query, get_analysis_output_query
from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value
from infrared_wrapper_api.config import settings


# make query to infrared api

# TODO async?
# can async requests be executed at bulk and each requests gets repeated until successful / or finally fails after 30 tries
# and then obtain a status whether all requests have finished and how many have finally failed
# should be used for buildings updating and deleting


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
            self.infrared_user_login()
            self.execute_query(query)

        if request.status_code != 200:
            raise Exception(
                f"Query failed to run by returning code of {request.status_code}. URL: {url} , Query: {query}, Headers: {headers}"
            )
        print(f"Query: {query.split('(')[0]} ||| execution time: {time.time() - start_time}")
        return request.json()


connector = InfraredConnector()


# for now every calcuation request creates a new infrared project, as calculation bbox is set on project level
def create_new_project(self):
    print("creating new project")
    self.delete_existing_project_with_same_name()

    # create new project
    query = wind.queries.create_project_query(
        self.user.uuid,
        self.name,
        self.bbox_sw_corner_wgs[0],
        self.bbox_sw_corner_wgs[1],
        self.bbox_size,
        self.analysis_grid_resolution,
    )
    # creation of new projects sometimes fails
    successfully_created = False
    try:
        new_project_response = execute_query(query, self.user)
        successfully_created = new_project_response["data"]["createNewProject"][
            "success"
        ]
        print("project name %s , created: %s" % (self.name, successfully_created))
        from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value
        project_uuid = get_value(
            new_project_response, ["data", "createNewProject", "uuid"]
        )
        project_uuid = project_uuid
        snapshot__uuid = get_root_snapshot_id(project_uuid)

        return project_uuid, snapshot__uuid

    except Exception as e:
        print("could not create new project", e)
        self.create_new_project()

    # TODO LUIS RETRY METHOD?
    if not successfully_created:
        print(
            "project not sucessfully created name %s , %s uuid"
            % (self.name, self.project_uuid)
        )
        # check if the project got initiated in the end. if not - delete it and recreate.
        time.sleep(1)
        create_new_project()


def delete_project(project_uuid: str):
    connector.execute_query(queries.delete_project_query(user_uuid, project_uuid))


def create_new_buildings(snapshot_uuid, new_buildings):
    query = queries.create_buildings(snapshot_uuid, new_buildings)
    new_bld_response = connector.execute_query(query)

    all_success = all(entry.get("success", False) for entry in new_bld_response["data"].values())
    # uuids = [entry.get("uuid") for entry in new_bld_response["data"].values()]

    if not all_success:
        print(
            f"could not create buildings! {new_bld_response}",
        )
        print(f"Query {query}")
        # TODO failed buildindings until it works?
        # create_new_building(new_building)


def get_all_building_uuids_for_project(project_uuid: str, snapshot_uuid: str) -> List[str]:
    snapshot_geometries = connector.execute_query(
        queries.get_geometry_objects_in_snapshot_query(snapshot_uuid)
    )

    building_path = [
        "data",
        "getSnapshotGeometryObjects",
        "infraredSchema",
        "clients",
        connector.user_uuid,
        "projects",
        project_uuid,
        "snapshots",
        snapshot_uuid,
        "buildings",
    ]
    try:
        buildings = get_value(snapshot_geometries, building_path)
    except Exception:
        print(f"could not get buildings for project uuid {project_uuid}")
        return {}

    return buildings.keys()


def delete_buildings(snapshot_uuid: str, building_uuids: List[str]):
    response = connector.execute_query(
        queries.delete_buildings(snapshot_uuid, building_uuids)
    )

    all_success = all(entry.get("success", False) for entry in response["data"].values())

    if not all_success:
        print(f"COULD NOT DELETE ALL BUILINGS {response.json()}")
        # TODO delete project then?


def get_all_projects_for_user():
    query = queries.get_projects_query(connector.user_uuid)

    projects = {}
    try:
        projects = get_value(
            connector.execute_query(query),
            ["data", "getProjectsByUserUuid", "infraredSchema", "clients", connector.user_uuid, "projects"]
        )

    except KeyError:
        print("no projects for user")

    return projects


def get_root_snapshot_id(project_uuid):
    query = queries.get_snapshot_query(project_uuid)

    snapshot = connector.execute_query(query)
    graph_snapshots_path = ["data", "getSnapshotsByProjectUuid", "infraredSchema", "clients", connector.user_uuid,
                            "projects", project_uuid, "snapshots"]

    return list(get_value(snapshot, graph_snapshots_path).keys())[0]  # root snapshot is the first (and only) one.
    # the root snapshot of the infrared project will be used to create buildings and perform analysis


def activate_sunlight_analysis_capability(user_uuid, user_token, project_uuid: str):
    query = queries.activate_sun_service_query(
        user_uuid, project_uuid
    )
    response = connector.execute_query(query, user_token)
    print("activate sunlight hours calc service", response)


def run_wind_wind_simulation(snapshot_uuid, wind_direction, wind_speed) -> str:
    query = run_wind_simulation_query(
        snapshot_uuid=snapshot_uuid,
        wind_direction=wind_direction,
        wind_speed=wind_speed
    )

    try:
        # TODO LOG REQUEST SOMEHOW
        response = connector.execute_query(query)
        return get_value(response, ["data", "runServiceWindComfort", "uuid"])
    except Exception as exception:
        print(f"calculation for wind FAILS! for snapshot {snapshot_uuid} with exception {exception}")


@retry(
    stop=stop_after_attempt(10),  # Maximum number of attempts
    wait=wait_exponential(multiplier=1, max=20),  # Exponential backoff with a maximum wait time of 10 seconds
    retry=retry_if_exception_type(KeyError)  # Retry only on APIError exceptions
)
def get_analysis_output(project_uuid: str, snapshot_uuid: str, result_uuid: str) -> str:
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
