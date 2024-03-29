import json
import numpy as np
from typing import List, Tuple
import geopandas as gpd
from shapely.geometry import box
import topojson as tp

from infrared_wrapper_api.config import settings


class InfraredResult:
    def __init__(
            self,
            analysisOutputN: float,
            analysisOutputE: float,
            analysisOutputS: float,
            analysisOutputW: float,
            analysisOutputX: int,
            analysisOutputY: int,
            analysisOutputData: List[List[float]]
    ):
        # set properties
        self.xmin = analysisOutputW
        self.xmax = analysisOutputE
        self.ymin = analysisOutputS
        self.ymax = analysisOutputN
        self.resolution_x = analysisOutputX
        self.resolution_y = analysisOutputY
        self.result_data = analysisOutputData

        self.check_result_dimensions()

    @classmethod
    def from_raw_result(cls, raw_result: dict):
        return InfraredResult(
            raw_result["analysisOutputN"],
            raw_result["analysisOutputE"],
            raw_result["analysisOutputS"],
            raw_result["analysisOutputW"],
            raw_result["analysisOutputX"],
            raw_result["analysisOutputY"],
            raw_result["analysisOutputData"]
        )

    def result_to_geojson(self):
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }

        # Create coordinate arrays for all grid cells
        x_coords = np.linspace(self.xmin, self.xmax, self.resolution_x)
        y_coords = np.linspace(self.ymin, self.ymax, self.resolution_y)

        for i in range(self.resolution_y - 1):
            for j in range(self.resolution_x - 1):
                value = self.result_data[i][j]
                coords = [
                    [
                        [x_coords[j], y_coords[i]],
                        [x_coords[j + 1], y_coords[i]],
                        [x_coords[j + 1], y_coords[i + 1]],
                        [x_coords[j], y_coords[i + 1]],
                        [x_coords[j], y_coords[i]]
                    ]
                ]

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": coords
                    },
                    "properties": {
                        "value": value
                    }
                }

                geojson["features"].append(feature)

        return geojson

    def check_result_dimensions(self):
        expected_sim_size = settings.infrared_calculation.infrared_sim_area_size

        if (
                self.xmax - self.xmin != expected_sim_size
                or self.ymax - self.ymin != expected_sim_size
        ):
            raise ValueError("sizes of simulation area and result do not match")


def georeference_infrared_result(
        raw_result: dict,
        total_bounds_simulation_area: Tuple[float, ...]
    ) -> dict:
    """
    Converts the result to a polygonized geojson
    Crops the buffer from the result, as values towards results' edges get unreliable.
    Dissolves pixels with same values into polygons
    """
    result = InfraredResult.from_raw_result(raw_result)

    result_geojson = result.result_to_geojson()
    result_gdf = gpd.GeoDataFrame.from_features(result_geojson["features"])
    geo_minx, geo_miny, _, _ = total_bounds_simulation_area

    # translate to position of simulation area
    result_gdf["geometry"] = result_gdf.translate(geo_minx, geo_miny)
    result_gdf = result_gdf.set_crs("EPSG:25832", allow_override=True)

    # crop the buffer area
    result_gdf = crop_buffer(result_gdf)

    # merge neighboring fields with same value
    result_gdf = result_gdf.dissolve(by="value").reset_index()

    # simplify the geometries with topojson (does not create gaps between simplified geoms)
    topo = tp.Topology(result_gdf, prequantize=False)
    result_gdf = topo.toposimplify(3).to_gdf()  # tolerance of 3 just delivered prettiest results
    result_gdf.geometry = result_gdf.geometry.buffer(0)  # fix invalid geoms

    # reproject and return geojson dict
    result_json = json.loads(result_gdf.to_crs("EPSG:4326").to_json())

    return result_json


def crop_buffer(gdf_with_metric_crs: gpd.GeoDataFrame):
    """
    crops the buffer from each side of the gdf
    """
    buffer = settings.infrared_calculation.simulation_area_buffer

    # make a mask that is the total bounds of the gdf, reduced by the buffer
    minx, miny, maxx, maxy = gdf_with_metric_crs.total_bounds
    mask_minx, mask_miny, mask_maxx, mask_maxy = minx + buffer, miny + buffer, maxx - buffer, maxy - buffer
    mask = box(mask_minx, mask_miny, mask_maxx, mask_maxy)

    return gpd.clip(gdf_with_metric_crs, mask)
