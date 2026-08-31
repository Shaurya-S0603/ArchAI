import pytest

from archai import create_app


@pytest.fixture()
def app():
    return create_app({"TESTING": True, "SECRET_KEY": "test-secret"})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def brief():
    return {
        "site_width_m": 18,
        "site_depth_m": 24,
        "household_size": 4,
        "bedrooms": 3,
        "bathrooms": 2,
        "other_rooms": ["study"],
        "style": "modern",
        "currency": "SGD",
        "budget": 900_000,
        "sustainability": False,
        "accessibility": True,
    }
