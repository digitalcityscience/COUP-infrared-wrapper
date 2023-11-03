import time
import json

from shapely.geometry import Polygon
import geopandas

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_root_snapshot_id, \
    get_all_building_uuids_for_project, delete_buildings, create_new_buildings
from infrared_wrapper_api.infrared_wrapper.infrared.models import InfraredProjectModel

config = None

"""Class to handle Infrared communication for a InfraredProject (one bbox to analyze)"""


class InfraredProject:
    def __init__(
            self,
            # project_data: InfraredProjectModel
            project_uuid: str,
    ):
        # set properties
        self.project_uuid = project_uuid

        self.snapshot_uuid = get_root_snapshot_id(project_uuid)

    # TODO wie machen wir das am besten mit wind vs sun simulation. 
    #  Sollte sichergestellt sein, das buildigns up to date sind + aber nicht doppelt updaten.
    # ich glaub es ist am besten das direkt in simulate.py zu machen. Dort erst update buildings aufrufen und dann die calc triggern
    def update_buildings_at_infrared(self, buildings: dict, simulation_area: dict):
        # await self.delete_all_buildings()   # loosing too much time here. Remember to delete buildings after sim!

        print("updating buildings for project")
        # TODO : can minx, miny be part of task description?
        buildings_gdf = geopandas.GeoDataFrame.from_features(buildings["features"], crs="EPSG:25832")
        simulation_area_gdf = geopandas.GeoDataFrame.from_features(simulation_area["features"], crs="EPSG:25832")

        # translate to local coord. system at 0,0
        minx, miny, _, _ = simulation_area_gdf.total_bounds
        buildings_gdf["geometry"] = buildings_gdf.translate(-minx, -miny)

        create_new_buildings(
            snapshot_uuid=self.snapshot_uuid,
            new_buildings=json.loads(buildings_gdf.explode(index_parts=True).to_json())  # creating multipolygons fails
        )

    # deletes all buildings for project on endpoint
    def delete_all_buildings(self):
        building_uuids = get_all_building_uuids_for_project(self.project_uuid, self.snapshot_uuid)

        if not building_uuids:
            print(f"no buildings to delete for project {self.project_uuid}")
            return

        delete_buildings(
            self.snapshot_uuid,
            building_uuids
        )


def create_new_project_at_infrared(
        # infrared_user: InfraredUser,
        name: str,
        bbox_utm: Polygon,  # bbox ist scheissegal, invent one.
        resolution=10
        # TODO resolution=InfraredCalculation.analysis_resolution,
) -> InfraredProjectModel:
    # DO THIS IN THE SETUP MODULE
    delete_existing_project_with_same_name()

    project_uuid, snapshot_uuid = create_project(

    )

    # clean the project from OSM geometries that infrared automatically creates
    delete_all_buildings()

    # update buildings here?

    return project_uuid, snapshot_uuid
