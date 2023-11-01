import time
import json

from shapely.geometry import Polygon
import geopandas

import infrared_wrapper_api.infrared_wrapper.infrared.queries as queries
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_root_snapshot_id, \
    get_all_building_uuids_for_project, delete_buildings, create_new_buildings
from infrared_wrapper_api.infrared_wrapper.infrared.models import InfraredProjectModel
from infrared_wrapper_api.config import InfraredCalculation
from infrared_wrapper_api.models.calculation_input import WindSimulationInput
from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value

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
        self.delete_all_buildings()

        print("updating buildings for project")
        # TODO : can minx, miny be part of task description?
        buildings_gdf = geopandas.GeoDataFrame.from_features(buildings["features"], crs="EPSG:25832")
        simulation_area_gdf = geopandas.GeoDataFrame.from_features(simulation_area["features"], crs="EPSG:25832")

        # translate to local coord. system at 0,0
        minx, miny, _, _ = simulation_area_gdf.total_bounds
        buildings_gdf["geometry"] = buildings_gdf.translate(-minx, -miny)

        create_new_buildings(
            snapshot_uuid=self.snapshot_uuid,
            new_buildings=json.loads(buildings_gdf.to_json())
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


    def trigger_sun_simulation_at_endpoint(self):
        # TODO calc_settings of type calc_settings

        # TODO activate_sunlight_analysis_capability(self.user, self.project_uuid)
        query = queries.run_sunlight_hours_service_query(self.snapshot_uuid)
        service_command = "runServiceSunlightHours"

        # make query to trigger result calculation on endpoint
        try:
            # TODO cityPyo.log_calculation_request(sim_type, result_uuid)
            res = execute_query(query, self.user_token)
            return get_value(res, ["data", service_command, "uuid"])

        except Exception as exception:
            print("calculation for SUN FAILS !")
            print(f"Exception: {exception}")

    # waits for the result to be available. Then crops it to the area of interest.
    # TODO potentially we crop the returned array here already to max calculation area --> bbox - 100m per side?
    def get_result(self, result_uuid) -> dict:
        tries = 0
        max_tries = 100
        response = execute_query(
            queries.get_analysis_output_query(result_uuid, self.snapshot_uuid),
            self.user_token,
        )

        # wait for result to arrive
        # TODO must be better way for this, like with yield?
        while (
                not get_value(response, ["data", "getAnalysisOutput", "infraredSchema"])
        ) and tries <= max_tries:
            tries += 1
            response = execute_query(
                queries.get_analysis_output_query(result_uuid, self.snapshot_uuid),
                self.user_token
            )
            time.sleep(2)  # give the API some time to calc something

        if not tries > max_tries:
            result = get_value(
                response,
                [
                    "data",
                    "getAnalysisOutput",
                    "infraredSchema",
                    "clients",
                    self.user.uuid,
                    "projects",
                    self.project_uuid,
                    "snapshots",
                    self.snapshot_uuid,
                    "analysisOutputs",
                    result_uuid,
                ],
            )
            return self.get_result_as_geojson(result)
        else:
            raise Exception("Could not get analysis_output from AIT", result_uuid)

    """ 
    **** Result conversion and cropping ****
    """

    # private
    # TODO get this out of here!
    def get_result_as_geojson(self, raw_result):
        tmp_geotif_raw_result = self.convert_result_to_geotif(
            raw_result, self.buffered_bbox_utm
        )
        geojson_raw_result = convert_tif_to_geojson(tmp_geotif_raw_result)

        return self.remove_buffer_from_result_then_clip_to_roi(geojson_raw_result)

    # private
    def convert_result_to_geotif(self, result, bbox):
        # save result as geotif so it can be easily cropped to roi
        geo_tif_path = export_result_to_geotif(
            result["analysisOutputData"], bbox, self.name
        )

        return geo_tif_path

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
