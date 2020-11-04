import pytest
from starlette.testclient import TestClient
from tortoise.contrib.test import finalizer, initializer

from bnstats import app


@pytest.fixture(scope="session", autouse=True)
def initialize_tests(request):
    initializer(["bnstats.models"], db_url="sqlite://:memory:", app_label="models")
    request.addfinalizer(finalizer)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)
