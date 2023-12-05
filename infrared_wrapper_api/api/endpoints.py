import logging

from celery.result import AsyncResult, GroupResult
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api import tasks
from infrared_wrapper_api.api.utils import unify_group_result
from infrared_wrapper_api.dependencies import celery_app
from infrared_wrapper_api.models.calculation_input import WindSimulationInput, SunSimulationInput

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tasks"])


@router.post("/processes/wind/execution")
async def execute_wind(
        calculation_input: WindSimulationInput,
):
    calculation_task = WindSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(simulation_input=jsonable_encoder(calculation_task), sim_type="wind")

    return {"taskId": result.get()}


@router.post("/processes/sun/execution")
async def execute_sun(
        calculation_input: SunSimulationInput,
):
    calculation_task = SunSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(jsonable_encoder(calculation_task), "sun")

    return {"taskId": result.get()}


@router.get("/jobs/{job_id}/results")
def get_job_results(job_id: str):
    group_result = GroupResult.restore(job_id, app=celery_app)

    if not group_result:
        raise HTTPException(status_code=404, detail=f"Result not found! Invalid job-id provided {job_id}")
    if not group_result.successful():
        raise HTTPException(status_code=404, detail="Result not ready yet")

    return unify_group_result(group_result)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    group_result = GroupResult.restore(job_id, app=celery_app)

    if not group_result:
        raise HTTPException(status_code=404, detail=f"Job not found! Invalid job-id provided {job_id}")

    # successful() returns true if all tasks successful.
    if group_result.successful():
        return {
            "status": "SUCCESS",
            "progress": 100
        }

    # Note that `complete` means `successful` in this context
    progress = group_result.completed_count() / len(group_result.results)

    # one of the jobs failed
    if group_result.failed():
        return {
            "status": "FAILURE",
            "progress": progress
        }

    if group_result.waiting():
        return {
            "status": "PENDING",
            "progress": progress
        }

    raise HTTPException(status_code=500, detail=f"Could not get status for job-id {job_id}")

