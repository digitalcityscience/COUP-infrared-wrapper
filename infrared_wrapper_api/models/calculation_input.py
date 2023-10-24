from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import Field

from infrared_wrapper_api.models.base import BaseModelStrict
from infrared_wrapper_api.utils import hash_dict, load_json_file

JSONS_DIR = Path(__file__).parent / "jsons"
BUILDINGS = JSONS_DIR / "buildings.json"


class InfraredSimulationTask(ABC):
    buildings: dict

    @abstractmethod
    def hash(self):
        pass

    @abstractmethod
    def celery_key(self):
        pass

    def get_buildings(self):
        return self.buildings

    # TODO should have a set/get results method?


class SimulationScenario(BaseModelStrict):
    buildings: dict


class WindSimulationInput(SimulationScenario):
    wind_speed: int = Field(..., ge=0, le=80, description="Maximum speed in km/h (0-80)")
    wind_direction: int = Field(..., ge=0, le=360, description="Wind direction in °")

    class Config:
        schema_extra = {
            "example": {
                "wind_speed": 42,
                "wind_direction": 40,
                "buildings": load_json_file(str(BUILDINGS.absolute())),
            }
        }

    @classmethod
    def from_dict(cls, input_dict):
        return WindSimulationInput(
            wind_speed=input_dict["wind_speed"],
            wind_direction=input_dict["wind_direction"],
            buildings=input_dict["buildings"]
        )


class WindSimulationTask(InfraredSimulationTask, WindSimulationInput):

    @property
    def hash(self) -> str:
        return hash_dict({"buildings": self.buildings})

    @property
    def settings_hash(self) -> str:
        return hash_dict(
            {
                "wind_speed": self.wind_speed,
                "wind_direction": self.wind_direction,
            }
        )

    @property
    def celery_key(self) -> str:
        return f"{self.hash}_{self.settings_hash}"


class SunSimulationInput(SimulationScenario):
    class Config:
        schema_extra = {
            "example": {
                "buildings": load_json_file(BUILDINGS),
            }
        }


class SunSimulationTask(InfraredSimulationTask, SunSimulationInput):
    @property
    def hash(self) -> str:
        return hash_dict({"buildings": self.buildings})

    @property
    def celery_key(self) -> str:
        return f"{self.hash}"


