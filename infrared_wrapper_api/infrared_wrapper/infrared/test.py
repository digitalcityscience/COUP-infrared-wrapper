import os
import json
import pytest
import geopandas as gpd

from unittest.mock import patch

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_building_uuids_for_project, \
    InfraredConnector, run_wind_wind_simulation, get_analysis_output, get_all_cut_prototype_projects_uuids
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_result import InfraredResult, crop_buffer, \
    georeference_infrared_result
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.utils import find_idle_infrared_project, update_infrared_project_status_in_redis
from infrared_wrapper_api.config import settings


@pytest.fixture
def sample_building_data():
    print(os.getcwd())
    with open("../../models/jsons/buildings.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_simulation_area():
    print(os.getcwd())
    with open("../../models/jsons/simulation_area.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_simulation_result():
    print(os.getcwd())
    with open("../../models/jsons/infrared_result_raw.json", "r") as f:
        return json.load(f)


def get_idle_project_id():
    # Mock functions
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        return find_idle_infrared_project(get_all_cut_prototype_projects_uuids())


def test_login():
    connector = InfraredConnector()
    connector.infrared_user_login()

    assert connector.token is not None
    assert connector.user_uuid is not None


def test_getting_idle_project():
    # Mock functions that require a redis instance to run.
    with patch("infrared_wrapper_api.utils.update_infrared_project_status_in_redis") as mock_update_status, \
            patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put, \
            patch("infrared_wrapper_api.dependencies.cache.get", return_value={"is_busy": False}) as mocK_cache_get:
        project_uuid = find_idle_infrared_project(get_all_cut_prototype_projects_uuids())

        # Assertions
        mocK_cache_get.assert_called()
        mock_update_status.assert_called_once_with(project_uuid=project_uuid, is_busy=True)
        assert project_uuid is not None


def test_create_infrared_project():
    # create buildings at infrared
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)

    assert project.snapshot_uuid is not None


def test_update_and_delete_buildings_at_infrared(sample_building_data, sample_simulation_area):
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)
    project.update_buildings_at_infrared(sample_building_data, sample_simulation_area)

    # Assertions
    building_count = len(sample_building_data["features"])
    assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == building_count

    # Run wind simulation
    result_uuid = run_wind_wind_simulation(
        snapshot_uuid=project.snapshot_uuid,
        wind_direction=45,
        wind_speed=15
    )
    assert result_uuid is not None

    # and fetch result
    result = get_analysis_output(project.project_uuid, project.snapshot_uuid, result_uuid)

    # check result looks like expected
    assert result is not None
    assert isinstance(result.get("analysisOutputData"), list)
    assert isinstance(result.get("analysisOutputData")[0], list)
    assert isinstance(result.get("analysisOutputData")[0][0], float)
    assert (result.get("analysisOutputData")[0][0] * 10) % 2 == 0  # result should be 0, 0.2, 0.4,...

    # check the dimensions of the simulation area
    assert result.get("analysisOutputE") == settings.infrared_calculation.infrared_sim_area_size
    assert result.get("analysisOutputN") == result.get("analysisOutputE")

    # Delete the buildings again
    project = InfraredProject(project_uuid)
    project.delete_all_buildings()
    assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == 0


def test_set_project_busy_status_false():
    project_uuid = get_idle_project_id()

    with patch("infrared_wrapper_api.dependencies.cache.put") as mock_cache_put:
        # set project as not busy.
        update_infrared_project_status_in_redis(project_uuid, False)
        mock_cache_put.assert_called_once_with(key=project_uuid, value={'is_busy': False})


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