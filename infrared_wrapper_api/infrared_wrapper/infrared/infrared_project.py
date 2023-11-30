import geopandas
import json

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_root_snapshot_id, \
    get_all_building_uuids_for_project, delete_buildings, delete_streets, create_new_buildings, \
    get_all_street_uuids_for_project

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

    # deletes all streets for project on endpoint
    def delete_all_streets(self):
        streets_uuids = get_all_street_uuids_for_project(self.project_uuid, self.snapshot_uuid)

        if not streets_uuids:
            print(f"no streets to delete for project {self.project_uuid}")
            return

        delete_streets(
            self.snapshot_uuid,
            streets_uuids
        )