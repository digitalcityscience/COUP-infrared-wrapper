from celery import signals, group, chain
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis, \
    get_all_infrared_project_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_wind_simulation

logger = get_task_logger(__name__)


# trigger calculation for a infrared project
@celery_app.task()
def task_do_wind_simulation(project_uuid: str, wind_sim_task: dict) -> dict:
    task = WindSimulationTask(**wind_sim_task)

    if result := cache.get(key=task.celery_key):
        logger.info(
            f"Result fetched from cache with key: {task.celery_key}"
        )
        return result

    logger.info(
        f"Starting calculation ...  Result with key: {task.celery_key} not found in cache."
    )

    return do_wind_simulation(
        project_uuid=project_uuid,
        wind_sim_task=wind_sim_task
    )


@celery_app.task()
def task_cache_result(geojson_result: dict, celery_key: str):
    # cache result if sucessful
    if geojson_result.get("features", []) == 0:
        logger.error("GOT EMPTY RESULT")
        return

    cache.put(key=celery_key, value=geojson_result)
    logger.info(f"Saved result with key {celery_key} to cache.")


@celery_app.task()
def compute_task_wind(simulation_input: dict) -> dict:

    # reproject buildings to metric system for internal use
    simulation_input["buildings"] = reproject_geojson(
        simulation_input["buildings"],
        "EPSG:4326",
        "EPSG:25832"
    )

    # split request in several simulation tasks with a simulation area of max 500m*500m
    simulation_tasks = create_simulation_tasks(simulation_input)
    logger.info(f"This simulation is split into {len(simulation_tasks)} subtasks")
    all_infrared_project_uuids = get_all_infrared_project_uuids()

    # trigger calculation and collect result for project in infrared_projects
    task_group = group(
        [
            # create task chain for each bbox. tasks in chain will be executed sequentially
            chain(
                task_do_wind_simulation.s(
                    project_uuid=find_idle_infrared_project(all_infrared_project_uuids),
                    wind_sim_task=jsonable_encoder(simulation_task)
                ),  # returns geojson result
                task_cache_result.s(simulation_task.celery_key)  # has return val of previous func as 1st arg
            )
            for simulation_task in simulation_tasks
        ]
    )

    group_result = task_group()
    group_result.save()

    return group_result.id


@celery_app.task()
def compute_task_sun(task_def: dict) -> dict:
    # TODO here we need to activate sun first at infrared
    raise NotImplementedError("no sun today")

    # return run_noise_calculation(task_def)


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
        # set project to be not busy again.
        update_infrared_project_status_in_redis(project_uuid=project_uuid, is_busy=False)
        logger.info(f"Set project to 'is_busy=False' for project: {project_uuid}")


if __name__ == "__main__":
    print("test")


    buildings = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "height": 40
                },
                "geometry": {
                    "coordinates": [
                        [
                            [
                                10.003865170424689,
                                53.5405666300465
                            ],
                            [
                                10.002973724330474,
                                53.53973588549286
                            ],
                            [
                                10.005870924135678,
                                53.53989240382907
                            ],
                            [
                                10.00578988358211,
                                53.540277677268165
                            ],
                            [
                                10.003865170424689,
                                53.5405666300465
                            ]
                        ]
                    ],
                    "type": "Polygon"
                }
            }
        ]
    }

    task_definition = {
        "buildings": buildings,
        "wind_speed": 20,
        "wind_direction": 45
    }

    compute_task_wind(task_definition)


