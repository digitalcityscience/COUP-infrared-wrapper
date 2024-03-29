from celery import group
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.models import SimType, ProjectStatus
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_simulation

logger = get_task_logger(__name__)


"""
This task is triggered by the endpoint.
It will create a split the simulation into several simulations of 500*500meters areas.
It will create a list of simulation_tasks with a simulation task for each area.
It will create a group task for all simulation_tasks
"""
@celery_app.task()
def task__compute(simulation_input: dict, sim_type: SimType) -> dict:
    print(f"RECEIVED SIMULATION REQUEST OF TYPE {sim_type}")

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
            # create task for each bbox.
            task__do_simulation.s(
                project_uuid=find_idle_infrared_project(all_project_uuids),
                sim_task=jsonable_encoder(simulation_task)
            )
            for simulation_task in simulation_tasks
        ]
    )

    group_result = task_group()
    group_result.save()

    return group_result.id


# trigger calculation for an infrared project
@celery_app.task()
def task__do_simulation(project_uuid: str, sim_task: dict) -> dict:
    """
    Doing a simulation for a 500*500meters simulation area.
    """

    # RETURN FROM CACHE IF POSSIBLE
    if result := cache.get(key=sim_task["celery_key"]):
        logger.info(
            f"Result fetched from cache with key: {sim_task['celery_key']}"
        )

        return result

    # RUN SIMULATION
    result = {}
    try:
        logger.info(
            f"Starting calculation ...  Result with key: {sim_task['celery_key']} not found in cache."
        )
        result = do_simulation(
            project_uuid=project_uuid,
            sim_task=sim_task
        )
    except Exception as e:
        logger.error(
            f"simulation for  sim_task {sim_task} failed with exception {e}"
        )
    else:
        # cache valid results
        if result and result.get("features", []):
            cache.put(key=sim_task.get("celery_key"), value=result)
            logger.info(f"Saved or renewed result with key {sim_task.get('celery_key')} to cache.")
    finally:
        # mark project as completed
        update_infrared_project_status_in_redis(project_uuid=project_uuid, status=ProjectStatus.TO_BE_CLEANED.value)

        return result
