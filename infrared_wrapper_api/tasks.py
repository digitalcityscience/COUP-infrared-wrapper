import geopandas as gpd
import json

from celery import signals, group, chain
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

# todo uncomment from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_bbox_matrix, create_simulation_tasks
from infrared_wrapper_api.infrared_wrapper.format_result import result_to_geojson
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_wind_simulation



from celery import Celery

from infrared_wrapper_api.cache import Cache
from infrared_wrapper_api.config import settings

cache = Cache(
    connection_config=settings.cache.connection,
    key_prefix=settings.cache.key_prefix,
    ttl_days=settings.cache.ttl_days,
)

celery_app = Celery(
    __name__, broker=settings.cache.broker_url, backend=settings.cache.result_backend
)


"""

TODOS

# write tests for infrared.
# trigger calculation -> return result_uuid and snapshotuuid + result geoference

# look at noise queries and their usage for making infrared queries

# return run_noise_calculation(task_def)

"""


logger = get_task_logger(__name__)

# trigger calculation for a infrared project
@celery_app.task()
def task_do_wind_simulation(
        project_uuid: str,
        wind_sim_task: dict):

    print("running sim task")
    # todo check for result of wind_sim_task in cache

    return do_wind_simulation(
        project_uuid,
        wind_sim_task
    )


@celery_app.task()
def compute_task_wind(task_def: dict) -> dict:

    print(task_def)

    simulation_tasks = create_simulation_tasks(task_def)

    # trigger calculation and collect result for project in infrared_projects
    task_group = group(
        [
            # create task chain for each bbox. tasks in chain will be executed sequentially
            chain(
                task_do_wind_simulation.s(
                    project_uuid=find_idle_infrared_project(),
                    wind_sim_task=jsonable_encoder(simulation_task)
                    #   TODO do the caching on that level? or not at all? yes!
                ),  # returns result_uuid
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


    if "task_do_wind_simulation" in kwargs["task"]:
        # set project to be not busy again.
        update_infrared_project_status_in_redis(project_uuid=kwargs['project_uuid'], is_busy=False)

        if state == "SUCCESS":
            key = "dkd"   # TODO get from SimulationTask input class
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


