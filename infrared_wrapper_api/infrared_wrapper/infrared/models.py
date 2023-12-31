from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Literal

SimType = Literal["wind", "sun"]

@dataclass_json
@dataclass
class ProjectStatus:
    is_busy: bool

