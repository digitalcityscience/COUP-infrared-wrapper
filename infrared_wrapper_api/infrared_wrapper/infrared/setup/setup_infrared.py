import random
from typing import List

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_building_uuids_for_project, \
    create_new_project, get_project_name, get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.utils import is_cut_prototype_project
from infrared_wrapper_api.api.utils import update_infrared_project_status_in_redis
from infrared_wrapper_api.config import settings


MIN_EMPTY_PROJECT_COUNT = settings.infrared_communication.infrared_projects_count


def get_count_empty_projects(all_project_uuids: List[str]) -> int:
    count_empty_projects = 0

    for project_uuid in all_project_uuids:
        # do not interfere with projects not used by / reserved for CUT-Prototype
        if is_cut_prototype_project(get_project_name(project_uuid)):
            project = InfraredProject(project_uuid)
            bld_uuids = get_all_building_uuids_for_project(project_uuid, project.snapshot_uuid)

            if len(bld_uuids) == 0:
                count_empty_projects += 1

    return count_empty_projects


def create_new_empty_project():
    random_hash = "%032x" % random.getrandbits(128)
    new_project_uuid = create_new_project(f"CUT_{random_hash}")

    # delete all buildings and streets
    new_project = InfraredProject(new_project_uuid)
    new_project.delete_all_buildings()
    new_project.delete_all_streets()

    print("created new empty project")


def delete_buildings_and_streets_for_these_projects(project_uuids: List[str]):
    print(f"cleaning up in project {project_uuids}")
    for project_uuid in project_uuids:
        project = InfraredProject(project_uuid)
        project.delete_all_buildings()
        project.delete_all_streets()


# TO BE RUN AS CHRON
if __name__ == "__main__":
    all_project_uuids = get_all_cut_prototype_projects_uuids()
    print(all_project_uuids)

    # preemptively delete all buildings and streets (in case they are mistakenly left from other processes)
    delete_buildings_and_streets_for_these_projects(all_project_uuids)

    # set all projects as not busy
    for project_uuid in all_project_uuids:
        update_infrared_project_status_in_redis(project_uuid=project_uuid, is_busy=False)

    # check how many empty projects we have
    count_empty = get_count_empty_projects(all_project_uuids)
    print(f"Currently {len(all_project_uuids)} CUT-PROTOTYPE projects at infrared for our user.")
    print(f"Of which {count_empty} are empty and ready to be used.")
    print(f"We should have a minimum of {MIN_EMPTY_PROJECT_COUNT} empty projects.")

    # create more empty projects if needed
    if count_empty < MIN_EMPTY_PROJECT_COUNT:
        for _ in range(MIN_EMPTY_PROJECT_COUNT - count_empty):
            create_new_empty_project()
