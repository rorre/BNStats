import json

from starlette.testclient import TestClient
from pytest_httpx import HTTPXMock
from bnstats.bnsite import request
from bnstats.routes import qat
from bnstats.models import Nomination, Reset


def test_first(client_without_middleware: TestClient, httpx_mock: HTTPXMock):
    request.api_key = "testing"
    qat.QAT_KEY = "testing"

    with open("tests/data/api/1209473.json") as f:
        httpx_mock.add_response(
            url="https://osu.ppy.sh/api/get_beatmaps?k=testing&s=1209473",
            json=json.load(f),
        )

    with open("tests/data/aiess/first.json") as f:
        res = client_without_middleware.post(
            "/qat/aiess", headers={"Authorization": "testing"}, json=json.load(f)
        )
        assert res.status_code == 200

    Reset.filter(userId=1).get()
    Nomination.filter(userId=1).get()


def test_error(client_without_middleware: TestClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://bn.mappersguild.com/users/relevantInfo", data="nope"
    )

    with open("tests/data/aiess/error.json") as f:
        res = client_without_middleware.post(
            "/qat/aiess", headers={"Authorization": "testing"}, json=json.load(f)
        )
        assert res.status_code == 500
        assert res.json() == {
            "status": 500,
            "messages": [
                "Cannot find user in database, maybe pishi site is falling behind?"
            ],
        }
