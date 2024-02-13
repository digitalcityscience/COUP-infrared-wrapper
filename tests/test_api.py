import json

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from infrared_wrapper_api.api.main import app
from typing import List
from tests.fixtures import sample_building_data_single_bbox, sample_simulation_input

client = TestClient(app)


class MockResult:

    def __init__(self, result=None):
        if result is None:
            result = {"features": []}
        self.result = result

    def get(self):
        # empty geojson mock
        return self.result


class MockGroupResult:
    def __init__(self, is_successful: bool, failed: bool, results: List[MockResult]):
        self.is_successful = is_successful
        self.is_failed = failed
        self.results: List[MockResult] = results

    def successful(self):
        return self.is_successful

    def failed(self):
        return self.is_failed

    def get(self):
        return "not implemented"


@pytest.fixture
def mock_result_not_ready():
    empty_mock_result = MockResult()
    return MockGroupResult(is_successful=False, failed=False, results=[empty_mock_result])


@pytest.fixture
def mock_result_ready():
    mock_result_content = {"features": [
        {
            "type": "Feature",
            "properties": {
                "value": 1
            },
            "geometry": {
                "coordinates": [
                    [
                        [
                            9.991281970821717,
                            53.508316561546536
                        ],
                        [
                            9.989940009272715,
                            53.50746527543134
                        ],
                        [
                            9.99083465030509,
                            53.50688000630859
                        ],
                        [
                            9.993697501609802,
                            53.50794412597509
                        ],
                        [
                            9.991281970821717,
                            53.508316561546536
                        ]
                    ]
                ],
                "type": "Polygon"
            }
        }
    ]}
    valid_single_result = MockResult(result=mock_result_content)

    return MockGroupResult(is_successful=True, failed=False, results=[valid_single_result])


def test_process_description(ogc_desc_wind):
    response = client.get(
        "/infrared/processes/wind-comfort"
    )
    assert response.status_code == 200
    assert ogc_desc_wind == response.json()


def test_wind(sample_simulation_input):
    with patch("infrared_wrapper_api.tasks.task__compute", return_value={"foo": "bar"}) as mock_task:
        response = client.post("/infrared/processes/wind-comfort/execution", json=sample_simulation_input)

        assert response.status_code == 201
        print(response.json())


def test_sun(sample_simulation_input):
    with patch("infrared_wrapper_api.tasks.task__compute", return_value={"foo": "bar"}) as mock_task:
        response = client.post("/infrared/processes/sunlight-hours/execution", json=sample_simulation_input)

        assert response.status_code == 201
        print(response.json())


def test_job_status_invalid_job_id():
    # Test invalid group task id
    with patch("celery.result.GroupResult.restore", return_value=None) as mock_restore:
        response = client.get("/infrared/jobs/abc123")

        assert response.status_code == 404
        assert json.loads(response.text).get("detail") == "no such job"


def test_job_status_valid_job_id(mock_result_ready):
    # Test invalid group task id
    with patch("celery.result.GroupResult.restore", return_value=mock_result_ready) as mock_restore:
        response = client.get("/infrared/jobs/abc123")

        assert response.status_code == 200
        assert response.json() == {'jobID': 'abc123', 'progress': 100, 'status': 'successful', 'type': 'process'}


def test_get_result_invalid_id():
    # Test invalid group task id
    with patch("celery.result.GroupResult.restore", return_value=None) as mock_restore:
        response = client.get("/infrared/jobs/abc123/results")

        assert response.status_code == 404


def test_get_result_not_ready(mock_result_not_ready):
    # test result not ready
    with patch("celery.result.GroupResult.restore", return_value=mock_result_not_ready) as mock_restore:
        response = client.get("/infrared/jobs/abc123/results")

        assert response.status_code == 404
        assert json.loads(response.text).get("detail") == "result not ready"


def test_get_result_ready(mock_result_ready):
    # test result ready
    with patch("celery.result.GroupResult.restore", return_value=mock_result_ready) as mock_restore:
        response = client.get("/infrared/jobs/abc123/results")

        assert response.status_code == 200

        # each MockResult had the same content, dissolves to 1 feature
        assert len(response.json()["result"]["geojson"]["features"]) == 1

