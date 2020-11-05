from unittest.mock import patch

from starlette.testclient import TestClient


def test_middleware(client: TestClient):
    # Disabled because of encode/starlette#472
    # https://github.com/encode/starlette/issues/472
    # res = client.get("/")
    # res.status_code == 200

    with patch("os.path.exists") as MockedExists:
        MockedExists.return_value = True
        res = client.get("/")
        res.status_code == 503
