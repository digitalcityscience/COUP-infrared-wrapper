from abc import abstractmethod
from pathlib import Path

from pydantic import Field

from infrared_wrapper_api.infrared_wrapper.infrared.models import SimType
from infrared_wrapper_api.models.base import BaseModelStrict
from infrared_wrapper_api.utils import hash_dict, load_json_file

JSONS_DIR = Path(__file__).parent / "jsons"
BUILDINGS = JSONS_DIR / "buildings_single_bbox.json"



class SimulationScenario(BaseModelStrict):
    buildings: dict

class WindSimulationInput(SimulationScenario):
    wind_speed: int = Field(..., ge=0, le=30, description="Maximum speed in m/s (0-30)")
    wind_direction: int = Field(..., ge=0, le=360, description="Wind direction in °")

    class Config:
        schema_extra = {
            "example": {
                "wind_speed": 10,
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


class SunSimulationInput(SimulationScenario):
    class Config:
        schema_extra = {
            "example": {
                "buildings": load_json_file(BUILDINGS),
            }
        }


# put project area there?
class InfraredSimulationTask(BaseModelStrict):
    simulation_area: dict  # geojson with area bbox

    @abstractmethod
    def sim_type(self):
        pass

    @abstractmethod
    def hash(self):
        pass

    @abstractmethod
    def celery_key(self):
        pass


class WindSimulationTask(InfraredSimulationTask, WindSimulationInput):

    @property
    def sim_type(self) -> SimType:
        return "wind"

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


class SunSimulationTask(InfraredSimulationTask, SunSimulationInput):

    @property
    def sim_type(self) -> SimType:
        return "sun"

    @property
    def hash(self) -> str:
        return hash_dict({"buildings": self.buildings})

    @property
    def celery_key(self) -> str:
        return f"{self.hash}_sun"