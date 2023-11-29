import logging

from celery.result import AsyncResult, GroupResult
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from infrared_wrapper_api import tasks
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


@router.get("/grouptasks/{group_task_id}")
def get_grouptask(group_task_id: str):
    # TODO handle invalid ids

    group_result = GroupResult.restore(group_task_id, app=celery_app)



    # Fields available
    # https://docs.celeryproject.org/en/stable/reference/celery.result.html#celery.result.ResultSet
    return {
        "grouptaskId": group_result.id,
        "tasksCompleted": group_result.completed_count(),
        "tasksTotal": len(group_result.results),
        "grouptaskProcessed": group_result.ready(),
        "grouptaskSucceeded": group_result.successful(),
        "results": [result.get() for result in group_result.results if result.ready()],
    }


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state
    if state == "FAILURE":
        state = f"FAILURE : {str(async_result.get())}"

    return {"status": state}
