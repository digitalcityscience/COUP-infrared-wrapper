from celery import signals, group, chain
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder
from typing import Literal

from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_simulation

logger = get_task_logger(__name__)


# trigger calculation for an infrared project
@celery_app.task()
def task__do_simulation(project_uuid: str, sim_task: dict) -> dict:

    # check if result for this task is already cached. Return from cache.
    if result := cache.get(key=sim_task["celery_key"]):
        logger.info(
            f"Result fetched from cache with key: {sim_task['celery_key']}"
        )
        return result

    logger.info(
        f"Starting calculation ...  Result with key: {sim_task['celery_key']} not found in cache."
    )

    return do_simulation(
        project_uuid=project_uuid,
        sim_task=sim_task
    )



@celery_app.task()
def task__cache_and_return_result(geojson_result: dict, celery_key: str) -> dict:
    # cache result if sucessful
    if geojson_result.get("features", []) == 0:
        logger.error("GOT EMPTY RESULT")
        return {}

    cache.put(key=celery_key, value=geojson_result)
    logger.info(f"Saved result with key {celery_key} to cache.")

    return geojson_result


@celery_app.task()
def task__compute(simulation_input: dict, sim_type: Literal["wind", "sun"]) -> dict:

    # reproject buildings to metric system for internal use
    simulation_input["buildings"] = reproject_geojson(
        simulation_input["buildings"],
        "EPSG:4326",
        "EPSG:25832"
    )

    # split request in several simulation tasks with a simulation area of max 500m*500m
    simulation_tasks = create_simulation_tasks(simulation_input, sim_type)
    logger.info(f"This simulation is split into {len(simulation_tasks)} subtasks")
    all_project_uuids = get_all_cut_prototype_projects_uuids()

    # trigger calculation and collect result for project in infrared_projects
    task_group = group(
        [
            # create task chain for each bbox. tasks in chain will be executed sequentially
            chain(
                task__do_simulation.s(
                    project_uuid=find_idle_infrared_project(all_project_uuids),
                    sim_task=jsonable_encoder(simulation_task)
                ),  # returns geojson result
                task__cache_and_return_result.s(simulation_task.celery_key)  # has return val of previous func as 1st arg
            )
            for simulation_task in simulation_tasks
        ]
    )

    group_result = task_group()
    group_result.save()

    return group_result.id



@signals.task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    state = kwargs.get("state")
    kwargs = kwargs.get("kwargs")

    # if state failure always set project_uuid busy:false

    if "task_do_wind_simulation" in str(task):
        if state == "SUCCESS":
            logger.info(f"simulation successfully run!")
        else:
            logger.error(f"Simulation of task {kwargs} failed with state {state}")

        project_uuid = kwargs.get("project_uuid")

        # delete buildings again
        infrared_project = InfraredProject(project_uuid)
        infrared_project.delete_all_buildings()

        # set project to be not busy again.
        update_infrared_project_status_in_redis(project_uuid=project_uuid, is_busy=False)
        logger.info(f"Set project to 'is_busy=False' for project: {project_uuid}")