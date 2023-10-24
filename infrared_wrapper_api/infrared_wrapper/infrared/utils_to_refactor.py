from infrared_wrapper_api.infrared_wrapper.infrared.infrared_connector import execute_query
import infrared_wrapper_api.infrared_wrapper.infrared.queries as queries
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_user import InfraredUser































# TODO delete dependency on queries and "make_query". Communication with INFRARED through connector


def delete_existing_project_with_same_name(infrared_user: InfraredUser, name):
    for project_uuid, project in infrared_user.get_all_projects().items():
        if project["projectName"] == name:
            print(f"project with name {name} already exists. deleting it")
            delete_response = execute_query(
                queries.delete_project_query(
                    infrared_user.uuid,
                    project_uuid
                ),
                infrared_user,
            )
            successfully_del = delete_response["data"]["deleteProject"]["success"]
            print(f"success deleting {successfully_del}")


# deletes all buildings for project on endpoint
def delete_all_buildings(project: InfraredProject):
    # get all geometries in snapshot
    snapshot_geometries = execute_query(
        queries.get_geometry_objects_in_snapshot_query(
            project.snapshot_uuid
        ),
        project.infrared_user,
    )

    building_ids_path = [
        "data",
        "getSnapshotGeometryObjects",
        "infraredSchema",
        "clients",
        project.infrared_user.uuid,
        "projects",
        project.project_uuid,
        "snapshots",
        project.snapshot_uuid,
        "buildings",
    ]
    try:
        buildings_uuids = get_all_buildings_at_endpoint().keys()
    except KeyError:
        print("no buildings in snapshot")
        return


    # TODO USE DELETE_BUILDING FUNCTION HERE FROM CONNECTOR
    # delete all buildings
    for building_uuid in buildings_uuids:
        execute_query(  # todo async
            queries.delete_building(
                project.snapshot_uuid,
                building_uuid
            ),
            project.infrared_user,
        )  # todo async


def get_all_buildings_at_endpoint():
    snapshot_geometries = execute_query(
        wind.queries.get_geometry_objects_in_snapshot_query(self.snapshot_uuid),
        self.user,
    )

    building_path = [
        "data",
        "getSnapshotGeometryObjects",
        "infraredSchema",
        "clients",
        self.user.uuid,
        "projects",
        self.project_uuid,
        "snapshots",
        self.snapshot_uuid,
        "buildings",
    ]
    try:
        buildings = get_value(snapshot_geometries, building_path)
    except:
        print("could not get buildings")
        return {}

    return buildings



# this might need to be used for a "create_new_project" method
# the root snapshot of the infrared project will be used to create buildings and perform analysis
# TODO refactor using get_value function
def get_root_snapshot_id(user: InfraredUser, project_uuid:str):
    graph_snapshots_path = [
        "data",
        "getSnapshotsByProjectUuid",
        "infraredSchema",
        "clients",
        user.uuid,
        "projects",
        project_uuid,
        "snapshots",
    ]
    snapshot = execute_query(
        queries.get_snapshot_query(project_uuid), user
    )
    if snapshot_uuid := list(get_value(snapshot, graph_snapshots_path).keys())[
        0
    ]:
        return snapshot_uuid
    else:
        raise ValueError("could not get snapshot uuid")

