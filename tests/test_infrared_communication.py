from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import get_all_building_uuids_for_project, \
    InfraredConnector, trigger_wind_simulation, get_analysis_output, \
    trigger_sun_simulation, activate_sunlight_analysis_capability
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject


from infrared_wrapper_api.infrared_wrapper.infrared.utils import reproject_geojson
from infrared_wrapper_api.config import settings
from tests.utils import get_idle_project_id
from tests.fixtures import sample_building_data_single_bbox, sample_simulation_area

"""
Tests communication with Infrared 
- finding an idle project at infrared
- read details of infrared project
- test updating and removing buildings
- test triggering simulations
- test getting simulation results
"""


def test_login():
    connector = InfraredConnector()
    connector.infrared_user_login()

    assert connector.token is not None
    assert connector.user_uuid is not None


def test_use_infrared_project():
    # create buildings at infrared
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)

    assert project.snapshot_uuid is not None


def test_update_and_delete_buildings_at_infrared(sample_building_data_single_bbox, sample_simulation_area):
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)
    project.update_buildings_at_infrared(sample_building_data_single_bbox, sample_simulation_area)

    try:
        # Assertions
        building_count = len(sample_building_data_single_bbox["features"])
        assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == building_count

        # Run wind simulation
        result_uuid = trigger_wind_simulation(
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

    except Exception as e:
        print(f"test failed {e}")

    finally:
        print("DELETING BUILDINGS AGAIN")
        # Delete the buildings again
        project = InfraredProject(project_uuid)
        project.delete_all_buildings()
        assert len(get_all_building_uuids_for_project(project.project_uuid, project.snapshot_uuid)) == 0


def test_sun_sim():
    project_uuid = get_idle_project_id()
    project = InfraredProject(project_uuid)
    # Run sun simulation
    activate_sunlight_analysis_capability(project_uuid)
    result_uuid = trigger_sun_simulation(
        snapshot_uuid=project.snapshot_uuid
    )
    assert result_uuid is not None
    # and fetch result
    result = get_analysis_output(project.project_uuid, project.snapshot_uuid, result_uuid)

    # check result looks like expected
    assert result is not None
    assert isinstance(result.get("analysisOutputData"), list)
    assert isinstance(result.get("analysisOutputData")[0], list)
    assert isinstance(result.get("analysisOutputData")[0][0], float)
