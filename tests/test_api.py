from fastapi.testclient import TestClient
from unittest.mock import patch

from infrared_wrapper_api.api.main import app
from tests.fixtures import sample_building_data, sample_simulation_input


client = TestClient(app)


def test_wind(sample_simulation_input):
    with patch("infrared_wrapper_api.tasks.task__compute", return_value={"foo": "bar"}) as mock_task:
        response = client.post("/task/wind", json=sample_simulation_input)

        assert response.status_code == 200
        print(response.json())


def test_sun(sample_simulation_input):
    with patch("infrared_wrapper_api.tasks.task__compute", return_value={"foo": "bar"}) as mock_task:
        response = client.post("/task/sun", json=sample_simulation_input)

        assert response.status_code == 200
        print(response.json())