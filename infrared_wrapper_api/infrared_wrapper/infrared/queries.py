from string import Template
import json


# returns a query string to create new building in snapshot

def create_project_query(user_uuid, name, sw_lat, sw_long, bbox_size, resolution):

    template = Template(
        """mutation {
            createNewProject (
            name: "$name"
            analysisGridResolution: $analysis_grid_resolution
            southWestLatitude: $south_west_latitude
            southWestLongitude: $south_west_longitude
            latitudeDeltaM: $latitude_delta_m
            longitudeDeltaM: $longitude_delta_m
            userUuid: "$user_uuid"
          ) {
            success
            uuid
          }
    }
    """)

    return template.safe_substitute({
        "name": name,
        "analysis_grid_resolution": resolution,
        "south_west_latitude": sw_lat,
        "south_west_longitude": sw_long,
        "latitude_delta_m": bbox_size,
        "longitude_delta_m": bbox_size,
        "user_uuid": user_uuid,
    })

# returns a query string to create new building in snapshot
def create_test_bld(building, snapshot_uuid):

    template = Template("""mutation
    {
        createNewBuilding(
        use: "$building_use"
        height: $building_height
        category: "site"
        geometry: "$building_geom"
        snapshotUuid: "$snapshot_uuid"
    ) {
        success
    uuid
    }
    }
    """)


    return template.safe_substitute({
        "building_use": building["use"],
        "building_height": building["height"],
        "building_geom": json.dumps(building["geometry"])[1:-1],
        "snapshot_uuid": snapshot_uuid
    })

# returns a query string to create new building in snapshot
def create_building_query(building, snapshot_uuid):

    template = Template("""mutation
    {
        createNewBuilding(
        use: "$building_use"
        height: $building_height
        category: "site"
        geometry: "$building_geom"
        snapshotUuid: "$snapshot_uuid"
    ) {
        success
    uuid
    }
    }
    """)

    return template.safe_substitute({
        "building_use": building["properties"]["use"],
        "building_height": building["properties"]["height"],
        "building_geom": json.dumps(building["geometry"])[1:-1],
        "snapshot_uuid": snapshot_uuid
    })


# unused for now
# returns a query string to create new street in snapshot
# def create_street_query(street_id):
#     street_geom = get_geom_for_street(street_id)
#     street_props = get_props_for_street(street_id)
#
#     template = Template("""
#     mutation {
#       createNewStreetSegment(
#         classification: "$street_class"
#         forwardLanes: $forward_lanes
#         backwardLanes: $backward_lanes
#         category: "site"
#         geometry: "$street_geom"
#         snapshotUuid: "$snapshot_uuid"
#       ) {
#     success
#     uuid
#       }
#     }
#     """)
#
#     return template.safe_substitute({
#         "street_class": street_props["street_class"],
#         "forward_lanes": street_props["backward_lanes"],
#         "backward_lanes": street_props["backward_lanes"],
#         "street_geom": street_geom,
#         "snapshot_uuid": snapshot_uuid
#     })


# TODO: run this before ?
#mutation {    modifyProject (      uuid: "2eced4cb-978f-47d0-b90d-512ef1748354"      sessionSettings: "{\"mode\":\"context\",\"analysis\":[{\"name\":\"Wind Comfort\",\"parameters\":[{\"name\":\"Wind Speed\",\"id\":\"windSpeed\",\"tag\":\"slider\",\"value\":\"20\"},{\"name\":\"Wind Direction\",\"id\":\"windDirection\",\"tag\":\"slider\",\"value\":\"0\"}]}]}"      userUuid:"28ac653e-b9f6-4ebf-a0e1-a152e4e37f24"    ) {      success    }  }
#mutation {\n runServiceWindComfort(\n snapshotUuid: \"91b16cd6-b1f9-4dc3-9722-2f8ddbcca083\"\n analysisName: \"Wind Comfort (0)\"\n windDirection: 90\n windSpeed: 20\n ) {\n success\n uuid\n } \n }"


def activate_sun_service_query(user_uuid, project_uuid):
    template = Template("""
    mutation {    
      modifyProject (
        uuid: "$project_uuid"
        sessionSettings: {"mode":"context","analysis":[{"name":"Sunlight Hours","version":0,"parameters":[],"uuid":null,"index":"0"}]}"
        userUuid:"$user_uuid"
      ) {
        success
        }
      }
    """)

    return template.safe_substitute({
        "project_uuid": project_uuid,
        "user_uuid": user_uuid
    })

def run_cfd_service_query(wind_direction, wind_speed, snapshot_uuid):
    template = Template("""
        mutation {
          runServiceWindComfort (
            snapshotUuid: "$snapshot_uuid"
            analysisName: "Wind Comfort (0)"
            windDirection: $wind_direction
            windSpeed: $wind_speed
          ) {
            success
            uuid
          }
        }
        """)

    return template.safe_substitute({
        "snapshot_uuid": snapshot_uuid,
        "wind_direction": wind_direction,
        "wind_speed": wind_speed
    })



def run_solar_rad_service_query(snapshot_uuid):
    template = Template("""
        mutation {
          runServiceSolarRadiation (
            snapshotUuid: "$snapshot_uuid"
            analysisName: "Solar Radiation 1"
          ) {
            success
            uuid
          }
        }
        """)

    return template.safe_substitute({
        "snapshot_uuid": snapshot_uuid,
    })


def run_sunlight_hours_service_query(snapshot_uuid):
    template = Template("""
        mutation {
          runServiceSunlightHours (
            snapshotUuid: "$snapshot_uuid"
            analysisName: "Sunlight Hours (0)"
          ) {
            success
            uuid
          }
        }
        """)

    return template.safe_substitute({
        "snapshot_uuid": snapshot_uuid,
    })


def get_analysis_output_query(uuid, snapshot_uuid):
    template = Template("""
        query {
          getAnalysisOutput (
            uuid: "$uuid"
            snapshotUuid: "$snapshot_uuid"
          ) {
            success
            infraredSchema
          }
        }
        """)

    return template.safe_substitute({
        "uuid": uuid,
        "snapshot_uuid": snapshot_uuid,
    })




def get_projects_query(user_uuid):
    """
    Execution time: 1.5sec
    """

    template = Template("""
                query {
                  getProjectsByUserUuid (
                    uuid: "$user_uuid"
                  ) {
                    success
                    infraredSchema
                  }
                }
            """)

    return template.safe_substitute({"user_uuid": user_uuid})


def delete_project_query(user_uuid, project_uuid):
    template = Template("""
                mutation {
                  deleteProject (
                    uuid: "$project_uuid"
                    userUuid: "$user_uuid"
                  ) {
                    success
                  }
                }
            """)

    return template.safe_substitute({"project_uuid": project_uuid, "user_uuid": user_uuid})


def get_snapshot_query(project_uuid):
    getSnapshotsQuery = Template("""
                query {
                  getSnapshotsByProjectUuid (
                    uuid: "$project_uuid"
                  ) {
                    success
                    infraredSchema
                  }
                }
            """)

    return getSnapshotsQuery.safe_substitute({"project_uuid": project_uuid})


def get_geometry_objects_in_snapshot_query(snapshot_uuid):
    template = Template("""
                query {
  getSnapshotGeometryObjects (
                    uuid: "$snapshot_uuid"
                  ) {
                    success
                    infraredSchema
                  }
                }
                """)

    return template.safe_substitute({"snapshot_uuid": snapshot_uuid})


def delete_building(snapshot_uuid, building_uuid):
    template = Template("""
                mutation {
                  deleteBuilding(
                    uuid: "$building_uuid",
                    snapshotUuid: "$snapshot_uuid"
                  ) {
                    success
                  }
                }
                """)

    return template.safe_substitute({"snapshot_uuid": snapshot_uuid, "building_uuid": building_uuid})


def delete_street(snapshot_uuid,street_uuid):
    template = Template("""
                mutation {
                  deleteStreetSegment(
                    uuid: "$street_uuid",
                    snapshotUuid: "$snapshot_uuid"
                  ) {
                    success
                  }
                }
                """)

    return template.safe_substitute({"snapshot_uuid": snapshot_uuid, "street_uuid": street_uuid})



