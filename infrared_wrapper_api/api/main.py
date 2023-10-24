import uvicorn
from fastapi import FastAPI

from infrared_wrapper_api.api.endpoints import router as tasks_router
from infrared_wrapper_api.config import settings

app = FastAPI(
    title=settings.title,
    descriprition=settings.description,
    version=settings.version,
)


@app.get("/health_check", tags=["ROOT"])
async def health_check():
    return "ok"


app.include_router(tasks_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
