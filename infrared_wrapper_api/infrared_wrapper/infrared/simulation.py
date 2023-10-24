import json
import logging
import os

from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
# from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_user import InfraredUser
from infrared_wrapper_api.dependencies import cache, celery_app
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_project_for_user, get_root_snapshot_id
from infrared_wrapper_api.infrared_wrapper.infrared.models import ProjectStatus, InfraredProjectModel
from infrared_wrapper_api.models.calculation_input import WindSimulationInput


def do_wind_simulation(
    infrared_user: dict,   # could be dataclass type
    project_uuid: str,
    buildings: dict,
    wind_speed: int,
    wind_direction: int
) -> str:
    print("buildings")
    print(type(buildings))
    print(buildings)

    infrared_project = InfraredProject(infrared_user, project_uuid)

    # TODO maybe it is best do it busy-marking, building updating and simulating on the proejct? move "private functions" out of class, but same file?"
    # TODO mark project as busy in cache.
    infrared_project.update_buildings_at_endpoint(buildings)
    result_uuid = infrared_project.trigger_wind_simulation_at_endpoint(wind_speed, wind_direction)

    return result_uuid





if __name__ == "__main__":
    infrared_user = InfraredUser()

    project_uuid, snapshot_uuid = find_idle_infrared_project()


