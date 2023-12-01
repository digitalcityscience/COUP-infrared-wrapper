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


@router.post("/task/wind")
async def process_task_wind(
    calculation_input: WindSimulationInput,
):
    calculation_task = WindSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(simulation_input=jsonable_encoder(calculation_task), sim_type="wind")

    return {"taskId": result.get()}\



@router.post("/task/sun")
async def process_task_sun(
    calculation_input: SunSimulationInput,
):
    calculation_task = SunSimulationInput(**calculation_input.dict())
    result = tasks.task__compute.delay(jsonable_encoder(calculation_task), "sun")

    return {"taskId": result.get()}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    async_result = AsyncResult(task_id, app=celery_app)

    response = {
        "taskId": async_result.id,
        "taskState": async_result.state,
        "taskSucceeded": async_result.successful(),
        "resultReady": async_result.ready(),
    }

    if async_result.ready():
        response["result"] = async_result.get()

    return response


@router.get("/jobs/{group_task_id}/results")
def get_grouptask_results(group_task_id: str):
    group_result = GroupResult.restore(group_task_id, app=celery_app)

    if not group_result:
        raise HTTPException(status_code=404, detail=f"Result not found! Invalid grouptask id provided {group_task_id}")
    if not group_result.ready():
        raise HTTPException(status_code=404, detail="Result not ready yet")

    return unify_group_result(group_result)


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state
    if state == "FAILURE":
        state = f"FAILURE : {str(async_result.get())}"

    return {"status": state}
