from typing import TypedDict, List
from dataclasses import dataclass
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class InfraredProjectModel:
    snapshot_uuid: str
    project_uuid: str
    # needed for both? creation might just need the wgs one.
    bbox_utm_wkt: str


@dataclass_json
@dataclass
class ProjectStatus:
    is_busy: bool
