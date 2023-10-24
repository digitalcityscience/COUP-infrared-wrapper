import requests
import os

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import delete_project, infrared_user_login, \
    get_all_project_for_user
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.dependencies import cache

cwd = os.getcwd()
config = None


class InfraredUser:
    """Class to handle Infrared communication for the InfraredUser"""

    def __init__(self, uuid=None, token=None):
        self.uuid = uuid
        self.token = token

        if not self.uuid:
            self.login()

    # logs in infrared user
    def login(self):
        username = settings.infrared_communication.user
        password = settings.infrared_communication.password

        self.uuid, self.token = infrared_user_login(username, password)


    @classmethod
    def from_dict(cls, input_dict):
        return InfraredUser(
            uuid=input_dict["uuid"],
            token=input_dict["token"],
        )


    # deletes all projects for the infrared user
    def delete_all_projects(self):
        for project_uuid in self.get_projects_uuids():
            delete_project(self, project_uuid)
            print(project_uuid, "deleted")


    # gets all the user's projects
    # TODO refactor later
    # def get_all_projects(self):
    #     all_projects = make_query(wind.queries.get_projects_query(self.uuid), self)
    #
    #     try:
    #         projects = get_value(
    #             all_projects,
    #             ["data", "getProjectsByUserUuid", "infraredSchema", "clients", self.uuid, "projects"]
    #         )
    #     except KeyError:
    #         print("no projects for user")
    #         return {}
    #
    #     return projects

    # gets all the user's projects



"""
# TODO move to 1 single file
# make query to infrared api
def make_query(query, token_cookie):
    ""
        Make query response
        auth token needs to be send as cookie
    ""
    # print(query)

    # AIT requested a sleep between the requests. To let their servers breath a bit.
    # time.sleep(0.5)

    request = requests.post(os.getenv("INFRARED_URL") + '/api', json={'query': query}, headers={'Cookie': token_cookie, 'origin': os.getenv('INFRARED_URL')})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))
"""



