import os

"""
Uses openapi.json (generated from fastapi + pydantic models) 
to create and serve OGC-API-PROCESSES compatible description jsons for 
- processes
- processes/process-id
- conformances
- landingpage
"""


def get_result_descriptions(process_id: str) -> dict:
    descriptions = {
        "wind-comfort": {
            "result": {
                "geojson": {
                    "title": "Result geojson with column 'value' for the results",
                    "description": "Wind Comfort  \
                        The 'wind comfort' service predicts a plane of Lawson Criteria categories, \
                         given an input wind direction and speed. The returned normalised values represent \
                         categories as seen in the following table:value lawson criteria category \
                         0.0 'Sitting Long' \
                         0.2 'Sitting Short' \
                         0.4 'Walking Slow' \
                        0.6 'Walking Fast' \
                        0.8 'Uncomfortable' \
                        1.0 'Dangerous' \
                        ",
                    "schema": {
                        "type": "object",
                        "contentMediaType": "application/geo+json",
                        "$ref": "https://geojson.org/schema/FeatureCollection.json"
                    }
                }
            }
        },
        "sunlight-hours": {
            "result": {
                "geojson": {
                    "title": "Result geojson with column 'value' for the results",
                    "description": "Sunlight Hours  \
                            The sunlight hours service predicts a plane representing how many hours a surface \
                            receives sunlight per day averaged over a year. \
                            There are no arguments, however, note that this model was trained on the solar \
                            characteristics of Vienna, AT. The returned normalised values \
                            need to be multiplied by 12 to return the results in hours per day. \
                            ",
                    "schema": {
                        "type": "object",
                        "contentMediaType": "application/geo+json",
                        "$ref": "https://geojson.org/schema/FeatureCollection.json"
                    }
                }
            }
        }
    }

    return descriptions[process_id]


def get_landingpage_json():
    return {
        "title": os.environ["APP_TITLE"],
        "description": "Simulate urban traffic noise for given roads and buildings. \
        Based on NoiseModelling v. by IFSTTAR",
        "links": [
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": "/openapi.json"
            },
            {
                "rel": "conformance",
                "type": "application/json",
                "title": "Conformance",
                "href": "/conformance"
            },
            {
                "rel": "http://www.opengis.net/def/rel/ogc/1.0/processes",
                "type": "application/json",
                "title": "Processes",
                "href": "/processes"
            },
        ]
    }


def get_processes(openapi_json: dict) -> dict:
    processes = []

    for path in openapi_json["paths"]:
        if post_request_info := openapi_json["paths"][path].get("post", None):
            if "process" in post_request_info["tags"]:
                processes.append(generate_process_description(openapi_json, path))

    return {"processes": processes}


def generate_process_description(openapi_json: dict, process_path: str) -> dict:
    print("generating process description for", process_path)

    for path in openapi_json["paths"]:
        if path == process_path:
            process_id = path.split("processes/")[1].split("/")[0]
            desc = {
                "id": process_id,
                "title": openapi_json["paths"][path]["post"]["summary"],
                "description": openapi_json["paths"][path]["post"]["summary"],
                "outputTransmission": ["value"],
                "jobControlOptions": ["async-execute"],
                "keywords": openapi_json["paths"][path]["post"]["summary"].split(" "),
                "inputs": {}
            }
            inputs_info_path = \
                openapi_json["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            inputs_class_name = inputs_info_path.split("/")[-1]
            inputs_info = openapi_json["components"]["schemas"][inputs_class_name]

            for input in inputs_info["properties"].keys():
                desc["inputs"][input] = {
                    "title": inputs_info["properties"][input]["title"],
                    "description": inputs_info["properties"][input].get(
                        "description",
                        inputs_info["properties"][input]["title"]
                    ),
                    "schema": inputs_info["properties"][input],
                    "minOccurs": int(input in inputs_info["required"]),
                    "maxOccurs": 1
                }

            desc["output"] = get_result_descriptions(process_id)

            return desc


def get_conformance():
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-processes/1.0/conf/core",
            "http://www.opengis.net/spec/ogcapi-processes/1.0/conf/json",
        ]
    }
