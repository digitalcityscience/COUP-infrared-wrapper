import geopandas as gpd
import json

from celery import signals, group, chain
from celery.utils.log import get_task_logger
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.infrared_wrapper.data_preparation import create_bbox_matrix
from infrared_wrapper_api.infrared_wrapper.format_result import result_to_geojson
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_user import InfraredUser
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.utils import find_idle_infrared_project
from infrared_wrapper_api.infrared_wrapper.infrared.simulation import do_wind_simulation

# from infrared_wrapper_api.infrared_wrapper.simulation

# from infrared_wrapper_api.models.calculation_input import NoiseTask


logger = get_task_logger(__name__)

# trigger calculation for a infrared project
@celery_app.task()
def task_do_wind_simulation(
        infrared_user: dict,
        project_uuid: str,
        buildings: dict,
        wind_speed: int,
        wind_direction: int):
    return do_wind_simulation(
        infrared_user,
        project_uuid,
        buildings,
        wind_speed,
        wind_direction
    )


@celery_app.task()
def compute_task_wind(task_def: dict, infrared_user: dict) -> dict:
    print(task_def)
    print(infrared_user)

    exit()

    # get bboxes for task.
    buildings = gpd.GeoDataFrame.from_features(task_def["buildings"]["features"], crs="EPSG:4326")
    buildings = buildings.to_crs("EPSG:25832")
    simulations_bboxes = create_bbox_matrix(
        buildings.unary_union.convex_hull,
        settings.infrared_calculation.max_bbox_size
    )

    # trigger calculation and collect result for project in infrared_projects
    task_group = group(
        [
            # create task chain for each bbox. tasks in chain will be executed sequentially
            chain(
                task_do_wind_simulation.s(
                    infrared_user=infrared_user,
                    # TODO : DO THIS FIRST: USING CACHE TO MARK BUSY; OTHERWISE ALL TESTS SUCK ;)
                    project_uuid=find_idle_infrared_project(infrared_user),
                    # TODO wind simulation task input class with celery key, instead of for all buildings!
                    # TODO do the caching on that level? or not at all? yes!
                    buildings=json.loads(buildings.clip(bbox).to_crs("EPSG:4326").to_json()),
                    wind_speed=task_def["wind_speed"],
                    wind_direction=task_def["wind_direction"]
                ),  # returns result_uuid
                # TODO also put project_uuid in result collect_result
                # collect_infrared_result.s(infrared_user),  # will have return val of previous func as first arg
                # TODO bbox to be put into result for georef later.
                # result_to_geojson(bbox)
            )
            for bbox in simulations_bboxes
        ]
    )

    print(len(task_group))


    group_result = task_group()
    group_result.save()

    return group_result.id




# fill with buildings  # or clip to
# simulations_bboxes

# initiate subtask


# --> do in subtask task: find projects that are idle

# update buildings

# trigger calculation -> return result_uuid and snapshotuuid + result geoference

# look at noise queries and their usage for making infrared queries

# return run_noise_calculation(task_def)


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


    # TODO if task task: <@task: infrared_wrapper_api.tasks.task_do_wind_simulation
    # TODO use kwargs['project_uuid'] to set project to be not busy again
    # TODO use kwargs["buildings"], wind_speed, wind_direction to cache

    return

    if state == "SUCCESS":
        key = "dkd"
        cache.put(key=key, value=result)
        logger.info(f"Saved result with key {key} to cache.")


if __name__ == "__main__":
    print("test")
    infrared_user = jsonable_encoder(InfraredUser())


    buildings = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "height": 15
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

    [
        {'uuid': '5b8db7a3-9fd4-455d-ad45-b4775e10a6d9',
      'token': 'InFraReD=eyJ0eXAiOiJKV1QiLCJhbGciOiJ'},
     '03ed1a63-bf78-4ce9-934e-1e78d8943561',
        {'type': 'FeatureCollection', 'features': [
        {'id': '0', 'type': 'Feature', 'properties': {'height': 32, 'use': 'some use'}, 'geometry': {'type': 'Polygon',
         'coordinates': [[[
             10.003865170424689,
             53.5405666300465],
             [
                 10.00578988358211,
                 53.540277677268165],
             [
                 10.005870924135678,
                 53.53989240382907],
             [
                 10.002973724330474,
                 53.53973588549285],
             [
                 10.003865170424689,
                 53.5405666300465]]]}}]},
     42, 40]
