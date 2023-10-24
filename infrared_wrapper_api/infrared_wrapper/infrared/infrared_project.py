import time
import json

from shapely.geometry import Polygon
import geopandas

import infrared_wrapper_api.infrared_wrapper.infrared.queries as queries
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import execute_query, create_new_building, \
    get_root_snapshot_id
from infrared_wrapper_api.infrared_wrapper.infrared.models import InfraredProjectModel
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_user import InfraredUser
from infrared_wrapper_api.config import InfraredCalculation
from infrared_wrapper_api.models.calculation_input import WindSimulationInput
from infrared_wrapper_api.infrared_wrapper.infrared.utils import get_value

config = None

"""Class to handle Infrared communication for a InfraredProject (one bbox to analyze)"""


class InfraredProject:
    def __init__(
            self,
            infrared_user: dict,
            # project_data: InfraredProjectModel
            project_uuid: str,
    ):
        # set properties
        self.user_uuid = infrared_user["uuid"]
        self.user_token = infrared_user["token"]
        self.project_uuid = project_uuid

        self.snapshot_uuid = get_root_snapshot_id(project_uuid, self.user_uuid, self.user_token)

    # TODO wie machen wir das am besten mit wind vs sun simulation. 
    #  Sollte sichergestellt sein, das buildigns up to date sind + aber nicht doppelt updaten.
    # ich glaub es ist am besten das direkt in simulate.py zu machen. Dort erst update buildings aufrufen und dann die calc triggern

    def update_buildings_at_endpoint(self, buildings):
        print("updating buildings for project")
        # TODO print(f"updating buildings for project {get_project_name(project_uuid)}")

        for new_building in buildings["features"]:
            create_new_building(self.snapshot_uuid, self.user_token, new_building)


    # TODO 1 method for each of the sims. awaiting suitable input then.
    # TODO calc_settings of type calc_settings
    def trigger_wind_simulation_at_endpoint(self, wind_speed: int, wind_direction: int) ->str:
        """
        returns UUID to obtain calculation result from @Infrared, when simulation done.
        """
        query = queries.run_cfd_service_query(
            wind_direction,
            wind_speed,
            self.snapshot_uuid,
        )

        # make query to trigger result calculation on endpoint
        try:
            # TODO LOG REQUEST SOMEHOW
            res = execute_query(query, self.user_token)
            return get_value(res, ["data", "runServiceWindComfort", "uuid"])
        except Exception as exception:
            print("calculation for wind FAILS!")
            print(f"with input{str(calc_settings)}")
            print(f"Exception: {exception}")

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

    # private
    def remove_buffer_from_result_then_clip_to_roi(self, input_geojson):

        # TODO remove buffer with numpy??

        # create a gdf of the unbuffered bbox. To clip to this.
        bbox_gdf = geopandas.GeoDataFrame(
            [self.bbox_wgs], columns=["geometry"], crs="EPSG:4326"
        )
        # remove bbox buffer
        clipped_gdf = geopandas.clip(make_gdf_from_geojson(input_geojson), bbox_gdf)
        # clip to ROI
        clipped_gdf = geopandas.clip(
            clipped_gdf, self.gdf_result_roi.to_crs("EPSG:4326")
        )

        return json.loads(clipped_gdf.to_json())


def create_new_project_at_infrared(
        infrared_user: InfraredUser,
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
