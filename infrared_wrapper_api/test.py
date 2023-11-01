import pytest
import json
import geopandas as gpd
import os

from infrared_wrapper_api.infrared_wrapper.data_preparation import create_simulation_tasks, create_bbox_matrix
from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.models.calculation_input import WindSimulationTask
from infrared_wrapper_api.config import settings


@pytest.fixture
def sample_building_data():
    print(os.getcwd())
    with open("./models/jsons/__all__buildings.json", "r") as f:
        geojson = json.load(f)
        return reproject_geojson(geojson, "EPSG:4326", "EPSG:25832")


@pytest.fixture
def sample_task_def(sample_building_data):
    return {
        "buildings": sample_building_data,
        "wind_speed": 10,
        "wind_direction": 45,
    }


def test_create_bbox_matrix(sample_building_data):
    bbox_matrix = create_bbox_matrix(gpd.GeoDataFrame.from_features(sample_building_data["features"], crs="EPSG:4326"))
    test_bbox = bbox_matrix[0]

    assert type(test_bbox) == gpd.GeoDataFrame

    # test bbox size
    minx, miny, maxx, maxy = test_bbox.total_bounds

    assert pytest.approx(maxx - minx) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer
    assert pytest.approx(maxy - miny) == settings.infrared_calculation.true_simulation_area_size \
           + 2 * settings.infrared_calculation.simulation_area_buffer


def test_create_simulation_tasks(sample_task_def, sample_building_data):
    sim_tasks = create_simulation_tasks(sample_task_def)

    for test_sim_task in sim_tasks:
        assert type(test_sim_task) == WindSimulationTask
        assert len(test_sim_task.buildings["features"]) > 0

        # test building in bbox
        sim_area_gdf = gpd.GeoDataFrame.from_features(test_sim_task.simulation_area["features"])
        buildings_gdf = gpd.GeoDataFrame.from_features(test_sim_task.buildings["features"])

        assert buildings_gdf.intersects(sim_area_gdf.unary_union.convex_hull).all()
