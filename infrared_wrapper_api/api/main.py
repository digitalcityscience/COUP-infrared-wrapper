import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every

from infrared_wrapper_api.api.endpoints import router as tasks_router
from infrared_wrapper_api.config import settings
from infrared_wrapper_api.infrared_wrapper.infrared.setup.setup_infrared import setup_infrared, cleanup_infrared_projects


API_PREFIX = "/infrared"

app = FastAPI(
    title=settings.title,
    descriprition=settings.description,
    version=settings.version,
    redoc_url=f"{API_PREFIX}/redoc",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
)


origins = [
    # "http://localhost",
    # "http://localhost:8080",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health_check", tags=["ROOT"])
async def health_check():
    return "ok"


@app.on_event("startup")
@repeat_every(seconds=60, wait_first=True)  # every minute
@app.get("/cleanup_infrared", tags=["ROOT"])
def clean_up_infrared():
    print("Cleaning up infrared projects...")
    return cleanup_infrared_projects()


app.include_router(tasks_router, prefix=API_PREFIX)


if __name__ == "__main__":
    print("Setting up infrared projects...")
    setup_infrared()
    uvicorn.run(app, host="0.0.0.0", port=80)
