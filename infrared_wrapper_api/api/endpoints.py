import logging
import os

from celery.result import GroupResult
from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi

from infrared_wrapper_api import tasks
from infrared_wrapper_api.api.documentation import get_processes, get_conformance, get_landingpage_json
from infrared_wrapper_api.api.utils import unify_group_result
from infrared_wrapper_api.dependencies import celery_app
from infrared_wrapper_api.models.calculation_input import WindSimulationInput, SunSimulationInput
from infrared_wrapper_api.models.ogc_job_status import StatusInfo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tasks"])


def generate_openapi_json():
    return get_openapi(title=os.environ["APP_TITLE"], version="1.0.0", routes=router.routes, openapi_version="3.0.0")


@router.get("/")
async def get_landing_page() -> dict:
    """
    OGC Processes 7.2 Retrieve the API Landing page | https://docs.ogc.org/is/18-062r2/18-062r2.html#toc23
    """
    return get_landingpage_json()


@router.get("/conformance")
async def get_conformances() -> dict:
    """
    OGC Processes 7.4 Declaration of conformances | https://docs.ogc.org/is/18-062r2/18-062r2.html#toc25
    """
    return get_conformance()


@router.get("/processes/{process_id}")
@router.get("/processes")
async def get_processes_json(process_id: str = None) -> dict:
    """
    OGC Processes 7.9 Process List https://docs.ogc.org/is/18-062r2/18-062r2.html#toc30
    OGC Processes 7.10 Process Description https://docs.ogc.org/is/18-062r2/18-062r2.html#toc31
    """
    processes = get_processes(generate_openapi_json())

    if process_id:
        for process in processes["processes"]:
            print(process)
            if process["id"] == process_id:
                return process

    return processes

@router.post(
    path="/processes/wind-comfort/execution",
    tags=["process"],
    status_code=201,
    summary="Wind Comfort Simulation"
)
async def execute_wind(
        calculation_input: WindSimulationInput,
        response: Response
):
    calculation_task = WindSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(simulation_input=jsonable_encoder(calculation_task), sim_type="wind")
    job_id = result.get()

    # OGC Processes Requirement 34 | /req/core/process-execute-success-async
    response.headers["Location"] = f"/infrared/jobs/{job_id}"

    return {
            "processID": "wind-comfort",
            "type": "process",
            "jobID": job_id,
            "status": StatusInfo.ACCEPTED.value
    }


@router.post(
    path="/processes/sunlight-hours/execution",
    tags=["process"],
    status_code=201,
    summary="Sunlight Hours Simulation"
)
async def execute_sun(
        calculation_input: SunSimulationInput,
        response: Response
):
    calculation_task = SunSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(jsonable_encoder(calculation_task), "sun")
    job_id = result.get()

    # OGC Processes Requirement 34 | /req/core/process-execute-success-async
    response.headers["Location"] = f"/infrared/jobs/{job_id}"

    return {
            "processID": "sunlight-hours",
            "type": "process",
            "jobID": job_id,
            "status": StatusInfo.ACCEPTED.value
    }


@router.get("/jobs/{job_id}/results")
def get_job_results(job_id: str):
    group_result = GroupResult.restore(job_id, app=celery_app)

    if not group_result:
        raise HTTPException(status_code=404, detail="no such job")

    if group_result.failed():
        # OGC 7.13.3 Requirement 46 | https://docs.ogc.org/is/18-062r2/18-062r2.html#toc34
        raise HTTPException(status_code=500, detail=str(group_result.get()))

    if not group_result.successful():
        # OGC 7.13.3 Requirement 45 | https://docs.ogc.org/is/18-062r2/18-062r2.html#toc34
        raise HTTPException(status_code=404, detail="result not ready")

    return {"result": {"geojson": unify_group_result(group_result)}}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    group_result = GroupResult.restore(job_id, app=celery_app)

    if not group_result:
        raise HTTPException(status_code=404, detail="no such job")

    response = {
        "type": "process",
        "jobID": job_id,
    }

    # successful() returns true if all tasks successful.
    if group_result.successful():
        response["status"] = StatusInfo.SUCCESS.value
        response["progress"] = 100

        return response

    # Note that `complete` means `successful` in this context
    progress = group_result.completed_count() / len(group_result.results)

    # one of the jobs failed
    if group_result.failed():
        response["status"] = StatusInfo.FAILURE.value
        response["progress"] = progress

        return response

    # jobs still running
    if group_result.waiting():
        response["status"] = StatusInfo.PENDING.value
        response["progress"] = progress

        return response

    raise HTTPException(status_code=500, detail=f"Could not get status for job-id {job_id}")
