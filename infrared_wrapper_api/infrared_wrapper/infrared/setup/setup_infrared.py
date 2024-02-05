import random
from typing import List

from infrared_wrapper_api.dependencies import cache
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_building_uuids_for_project, \
    create_new_project, get_project_name, get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus
from infrared_wrapper_api.utils import is_cut_prototype_project
from infrared_wrapper_api.api.utils import update_infrared_project_status_in_redis
from infrared_wrapper_api.config import settings

MIN_EMPTY_PROJECT_COUNT = settings.infrared_communication.infrared_projects_count


def cleanup_project(project_uuid: str):
    infrared_project = InfraredProject(project_uuid)

    try:
        # clean up project
        print("Cleaning up project {}".format(project_uuid))
        infrared_project.delete_all_buildings()
    except Exception as e:
        print(f"cleaning up failed. creating a new project instead. Error: {e}")
        infrared_project.delete_this_project()
        create_new_empty_project()
    else:
        # set project to be not busy again.
        update_infrared_project_status_in_redis(project_uuid=project_uuid, status=ProjectStatus.IDLE.value)
        print(f"cleanup complete {project_uuid}")


def get_count_empty_projects(all_project_uuids: List[str]) -> int:
    count_empty_projects = 0

    for project_uuid in all_project_uuids:
        if is_cut_prototype_project(get_project_name(project_uuid)):
            project = InfraredProject(project_uuid)
            bld_uuids = get_all_building_uuids_for_project(project_uuid, project.snapshot_uuid)

            if len(bld_uuids) == 0:
                count_empty_projects += 1
                # make sure its marked as idle
                update_infrared_project_status_in_redis(project_uuid=project_uuid, status=ProjectStatus.IDLE.value)

    return count_empty_projects


def create_new_empty_project():
    random_hash = "%032x" % random.getrandbits(128)
    new_project_uuid = create_new_project(name=f"CUT_{random_hash}")

    # delete all buildings and streets
    new_project = InfraredProject(new_project_uuid)
    new_project.delete_all_buildings()
    new_project.delete_all_streets()

    # on InfraredProject have name and status. put that in redis.
    update_infrared_project_status_in_redis(project_uuid=new_project_uuid, status=ProjectStatus.IDLE.value)

    print("created new empty project")


def cleanup_infrared_projects():
    all_project_uuids = get_all_cut_prototype_projects_uuids()
    idle_project_ids = []
    for project_uuid in all_project_uuids:
        project_info = cache.get(key=project_uuid)
        if project_info and project_info.get("status") == ProjectStatus.IDLE.value:
            idle_project_ids.append(project_uuid)
        if project_info and project_info.get("status") == ProjectStatus.TO_BE_CLEANED.value:
            cleanup_project(project_uuid=project_uuid)
            idle_project_ids.append(project_uuid)

    return idle_project_ids


def setup_infrared() -> List[dict]:
    """
    Cleans buildings from all completed infrared projects
    and ensures that we have enough idle projects waiting at infrared.
    """
    cleanup_infrared_projects()
    all_project_uuids = get_all_cut_prototype_projects_uuids()

    # check how many empty projects we have
    count_empty = get_count_empty_projects(all_project_uuids)
    print(f"Currently {len(all_project_uuids)} CUT-PROTOTYPE projects at infrared for our user.")
    print(f"Of which {count_empty} are empty and ready to be used.")
    if count_empty < MIN_EMPTY_PROJECT_COUNT:
        print(f"We should have a minimum of {MIN_EMPTY_PROJECT_COUNT} empty projects.")

    # create more empty projects if needed
    if count_empty < MIN_EMPTY_PROJECT_COUNT:
        for _ in range(MIN_EMPTY_PROJECT_COUNT - count_empty):
            create_new_empty_project()

    # list of all projects' status
    return [
        {
            "name": get_project_name(project_uuid),
            "status": cache.get(key=project_uuid).get("status", None)
        }
        for project_uuid in get_all_cut_prototype_projects_uuids()
    ]


if __name__ == "__main__":
    setup_infrared()
