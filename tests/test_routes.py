from starlette.testclient import TestClient


def test_homepage(client_without_middleware: TestClient):
    assert client_without_middleware.get("/").status_code == 200


# TODO: The rest of the routes
