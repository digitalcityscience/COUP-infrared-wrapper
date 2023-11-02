import geopandas as gpd
import json

from celery import signals, group, chain
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_wind_simulation


logger = get_task_logger(__name__)


# trigger calculation for a infrared project
@celery_app.task()
def task_do_wind_simulation(
        project_uuid: str,
        wind_sim_task: dict) -> dict:

    task = WindSimulationTask(**wind_sim_task)

    if result := cache.get(key=task.celery_key):
        logger.info(
            f"Result fetched from cache with key: {task.celery_key}"
        )
        return result

    logger.info(
        f"Result with key: {task.celery_key} not found in cache. Starting calculation ..."
    )

    return do_wind_simulation(
        project_uuid,
        wind_sim_task
    ).to_dict()


@celery_app.task()
def compute_task_wind(simulation_input: dict)-> dict:

    # reproject buildings to metric system for internal use
    simulation_input["buildings"] = reproject_geojson(
        simulation_input["buildings"],
        "EPSG:4326",
        "EPSG:25832"
    )

    # split request in several simulation tasks with a simulation area of max 500m*500m
    simulation_tasks = create_simulation_tasks(simulation_input)

    # trigger calculation and collect result for project in infrared_projects
    task_group = group(
        [
            # create task chain for each bbox. tasks in chain will be executed sequentially
            chain(
                task_do_wind_simulation.s(
                    project_uuid=find_idle_infrared_project(),
                    wind_sim_task=jsonable_encoder(simulation_task)
                ),  # returns result_uuid and project uuid!
                # TODO also put project_uuid in result collect_result
                # collect_infrared_result.s(infrared_user),  # will have return val of previous func as first arg
                # TODO bbox to be put into result for georef later.
                # result_to_geojson(simulation_task.simulation_area)
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
    args = kwargs.get("args")
    kwargs = kwargs.get("kwargs")
    result = kwargs.get("retval")

    print(f"task_id: {task_id}")
    print(f"task: {task}")
    print(f"args: {args}")
    print(f"kwargs: {kwargs}")
    print(f"uuuuuuuuid: {kwargs['project_uuid']}")
    print(f"wind_sim_task: {kwargs['wind_sim_task']}")

    if "task_do_wind_simulation" in kwargs["task"]:
        # set project to be not busy again.
        update_infrared_project_status_in_redis(project_uuid=kwargs['project_uuid'], is_busy=False)
        logger.info(f"Set project to 'is_busy=False' for project: {kwargs['project_uuid']}")

        if state == "SUCCESS":
            # cache result if sucessful
            key = WindSimulationTask(**kwargs['wind_sim_task']).celery_key
            cache.put(key=key, value=result)
            logger.info(f"Saved result with key {key} to cache.")


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

    compute_task_wind(task_definition, infrared_user)


