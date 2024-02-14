from dataclasses import dataclass
from typing import Literal
from enum import Enum

SimType = Literal["wind", "sun"]


class ProjectStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    TO_BE_CLEANED = "to_be_cleaned"
