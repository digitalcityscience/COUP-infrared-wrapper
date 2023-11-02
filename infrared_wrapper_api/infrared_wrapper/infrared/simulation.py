import geopandas as gpd

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import run_wind_wind_simulation, \
    get_analysis_output
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_result import georeference_infrared_result

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def do_wind_simulation(
        project_uuid: str,
        wind_sim_task: dict
) -> dict:
    infrared_project = InfraredProject(project_uuid)
    infrared_project.update_buildings_at_infrared(
        wind_sim_task["buildings"],
        wind_sim_task["simulation_area"]
    )

    logger.info("Triggering simulation at infrared")

    result_uuid = run_wind_wind_simulation(
        snapshot_uuid=infrared_project.snapshot_uuid,
        wind_direction=wind_sim_task["wind_direction"],
        wind_speed=wind_sim_task["wind_speed"]
    )

    logger.info(f"Simulation result has infrared uuid {result_uuid}")
    logger.info("Trying to collect result now (waiting to be ready)")

    result_raw = get_analysis_output(
        project_uuid,
        infrared_project.snapshot_uuid,
        result_uuid
    )

    logger.info("Converting raw result into geojson")

    sim_area_gdf = gpd.GeoDataFrame.from_features(wind_sim_task["simulation_area"]["features"])

    return georeference_infrared_result(result_raw, sim_area_gdf.total_bounds)

