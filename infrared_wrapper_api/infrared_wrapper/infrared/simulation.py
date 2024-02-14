import geopandas as gpd

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import trigger_wind_simulation, \
    get_analysis_output, activate_sunlight_analysis_capability, trigger_sun_simulation
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_result import georeference_infrared_result

from celery.utils.log import get_task_logger

from infrared_wrapper_api.utils import log_request

logger = get_task_logger(__name__)


def do_simulation(
    project_uuid: str,
    sim_task: dict
) -> dict:
    infrared_project = update_buildings_at_infrared(project_uuid, sim_task)
    sim_type = sim_task["sim_type"]

    if sim_type == "wind":
        result_uuid = trigger_wind_simulation(
            snapshot_uuid=infrared_project.snapshot_uuid,
            wind_direction=sim_task["wind_direction"],
            wind_speed=sim_task["wind_speed"]
        )
    elif sim_type == "sun":
        result_uuid = trigger_sun_simulation(
            snapshot_uuid=infrared_project.snapshot_uuid,
        )
    else:
        raise NotImplementedError(f"requested unknown simulation type {sim_type}")

    logger.info(f"Simulation result has infrared uuid {result_uuid}")

    # increase the logged sim requests by 1
    log_request(sim_type)

    return collect_and_format_result(infrared_project, sim_task, result_uuid)


def update_buildings_at_infrared(project_uuid, task: dict) -> InfraredProject:
    logger.info(f"Updating buildings at infrared for project {project_uuid}")
    infrared_project = InfraredProject(project_uuid)
    infrared_project.update_buildings_at_infrared(
        task["buildings"],
        task["simulation_area"]
    )

    if task["sim_type"] == "sun":
        activate_sunlight_analysis_capability(project_uuid)

    return infrared_project


def collect_and_format_result(infrared_project: InfraredProject, sim_task: dict, result_uuid: str) -> dict:
    logger.info("Trying to collect result now (waiting to be ready)")
    result_raw = get_analysis_output(
        infrared_project.project_uuid,
        infrared_project.snapshot_uuid,
        result_uuid
    )

    logger.info("Converting raw result into geojson")
    return georeference_infrared_result(
        result_raw,
        gpd.GeoDataFrame.from_features(sim_task["simulation_area"]["features"]).total_bounds
    )