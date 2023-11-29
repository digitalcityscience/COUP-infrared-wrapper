import geopandas as gpd

from infrared_wrapper_api.config import settings
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_result import InfraredResult, crop_buffer, \
    georeference_infrared_result
from tests.fixtures import sample_simulation_result, sample_simulation_area


def test_handling_result(sample_simulation_result):
    infrared_result = InfraredResult.from_raw_result(sample_simulation_result)
    geojson_result = infrared_result.result_to_geojson()

    assert len(geojson_result["features"]) > 0
    sample_value = geojson_result["features"][0]["properties"]["value"]
    assert isinstance(sample_value, float)
    assert (sample_value * 10) % 2 == 0  # result should be 0, 0.2, 0.4,...

    gdf = gpd.GeoDataFrame.from_features(geojson_result["features"])

    # check the cropping
    cropped = crop_buffer(gdf)
    assert cropped.within(gdf.unary_union.convex_hull).all()
    assert gdf.unary_union.convex_hull.area > cropped.unary_union.convex_hull.area

    total_bounds_outer = gdf.total_bounds
    total_bounds_cropped = cropped.total_bounds

    # sourcery skip: no-loop-in-tests
    for val1, val2 in zip(total_bounds_outer, total_bounds_cropped):
        assert abs(val1 - val2) == settings.infrared_calculation.simulation_area_buffer


def test_getting_final_georeferenced_result(sample_simulation_result, sample_simulation_area):
    sim_area_gdf = gpd.GeoDataFrame.from_features(sample_simulation_area["features"], "EPSG:25832")

    result = georeference_infrared_result(sample_simulation_result, sim_area_gdf.total_bounds)
    result_gdf = gpd.GeoDataFrame.from_features(result["features"])

    # check that the result really is within the simulation area.
    assert result_gdf.within(sim_area_gdf.to_crs("EPSG:4326").unary_union.convex_hull).all()
