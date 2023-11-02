from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import run_wind_wind_simulation
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.models import ResultLookUpInfo


def do_wind_simulation(
    project_uuid: str,
    wind_sim_task: dict
) -> ResultLookUpInfo:
    infrared_project = InfraredProject(project_uuid)
    infrared_project.update_buildings_at_infrared(
        wind_sim_task["buildings"],
        wind_sim_task["simulation_area"]
    )

    result_uuid = run_wind_wind_simulation(
        snapshot_uuid=infrared_project.snapshot_uuid,
        wind_direction=wind_sim_task["wind_direction"],
        wind_speed=wind_sim_task["wind_speed"]
    )

    return ResultLookUpInfo(
        project_uuid= project_uuid,
        result_uuid= result_uuid
    )

