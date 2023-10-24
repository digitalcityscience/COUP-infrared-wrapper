import shapely

from shapely.geometry import Polygon

from infrared_wrapper_api.infrared_wrapper.infrared.infrared_user import InfraredUser
from infrared_wrapper_api.infrared_wrapper.infrared.infrared_project import InfraredProject, create_new_project_at_infrared
from infrared_wrapper_api.infrared_wrapper.infrared.models import InfraredProjectModel

from infrared_wrapper_api.config import settings


def test_create_user():

    user = InfraredUser()

    assert type(user.uuid) == str
    assert type(user.token) == str

    return user


def test_create_project(user: InfraredUser):
    bbox = Polygon([
          [
            [
              9.986072480974428,
              53.516982783075576
            ],
            [
              9.986072480974428,
              53.51663660678955
            ],
            [
              9.986751729573513,
              53.51663660678955
            ],
            [
              9.986751729573513,
              53.516982783075576
            ],
            [
              9.986072480974428,
              53.516982783075576
            ]
          ]
        ])

    project_data = create_new_project_at_infrared(
        user,
        "test_project",
        bbox,
        resolution=settings.infrared_calculation.analysis_resolution
    )

    project = InfraredProject(user, project_data)



if __name__ == "__main__":

    user = test_create_user()
    test_create_project(user)

