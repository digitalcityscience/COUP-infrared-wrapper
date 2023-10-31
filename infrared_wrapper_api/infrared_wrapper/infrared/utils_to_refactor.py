


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

