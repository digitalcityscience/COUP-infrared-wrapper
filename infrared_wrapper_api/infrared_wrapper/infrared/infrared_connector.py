import os
import requests
import time

from infrared_wrapper_api.infrared_wrapper.infrared import queries
from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value


# make query to infrared api

# TODO async?
# can async requests be executed at bulk and each requests gets repeated until successful / or finally fails after 30 tries
# and then obtain a status whether all requests have finished and how many have finally failed
# should be used for buildings updating and deletingdi


def infrared_user_login(username, password) -> tuple[str]:
    url = os.getenv("INFRARED_URL")  # or passed?
    user_creds = {"username": username, "password": password}
    request = requests.post(os.getenv("INFRARED_URL"), json=user_creds)

    if request.status_code != 200:
        raise Exception(
            f"Failed to login to infrared by returning code of {request.status_code}"
        )
    # get the auth token from the returned cookie
    print(request.cookies)
    uuid = request.cookies.get("InFraReDClientUuid")
    token = "InFraReD=" + request.cookies.get("InFraReD")

    return uuid, token

def execute_query(query: str, token:str):
    """
        Make query response
        auth token needs to be send as cookie
    """
    print(f"Query: {query.split('(')[0]}")
    start_time = time.time()

    # AIT requested a sleep between the requests. To let their servers breath a bit.
    token_cookie = token
    url = os.getenv("INFRARED_URL") + '/api'
    headers = {'Cookie': token_cookie, 'origin': os.getenv('INFRARED_URL')}
    request = requests.post(url, json={'query': query}, headers=headers)

    if request.status_code != 200:
        raise Exception(
            f"Query failed to run by returning code of {request.status_code}. URL: {url} , Query: {query}, Headers: {headers}"
        )
    print(f"query execution time: {time.time() - start_time}")
    return request.json()


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



def delete_project(user_uuid, user_token, project_uuid: str):
    execute_query(queries.delete_project_query(user_uuid, project_uuid), user_token)


def create_new_building(snapshot_uuid, user_token, new_building):

    query = queries.create_building_query(new_building, snapshot_uuid)
    new_bld_response = execute_query(query, user_token)
    uuid = get_value(new_bld_response, ["data", "createNewBuilding", "uuid"])

    if not uuid:
        print(
            f"could not create building! {new_bld_response}",
        )
        print(f"Query {query}")
        # TODO retry until it works
        # create_new_building(new_building)


def delete_building(self, building_uuid):
    execute_query(
        queries.delete_building(self.snapshot_uuid, building_uuid), self.user
    )



def activate_sunlight_analysis_capability(user_uuid, user_token, project_uuid: str):
    query = queries.activate_sun_service_query(
        user_uuid, project_uuid
    )
    response = execute_query(query, user_token)
    print("activate sunlight hours calc service", response)


def get_all_project_for_user(user_uuid: str, user_token: str):
    query = queries.get_projects_query(user_uuid)

    projects = {}
    try:
        projects = get_value(
            execute_query(query, user_token),
            ["data", "getProjectsByUserUuid", "infraredSchema", "clients", user_uuid, "projects"]
        )

    except KeyError:
        print("no projects for user")

    return projects


def get_root_snapshot_id(project_uuid, user_uuid, user_token):
    query = queries.get_snapshot_query(project_uuid)

    snapshot = execute_query(query, user_token)
    graph_snapshots_path = ["data", "getSnapshotsByProjectUuid", "infraredSchema", "clients",user_uuid,
                            "projects", project_uuid, "snapshots"]

    return list(get_value(snapshot, graph_snapshots_path).keys())[0]  # root snapshot is the first (and only) one.
    # the root snapshot of the infrared project will be used to create buildings and perform analysis
