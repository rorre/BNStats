import json

from starlette.testclient import TestClient
from pytest_httpx import HTTPXMock
from bnstats import routine
from bnstats.routes import qat
from bnstats.models import Nomination, Reset


def test_first(client: TestClient, httpx_mock: HTTPXMock):
    routine.API_KEY = "testing"
    qat.QAT_KEY = "testing"

    with open("tests/data/api/1209473.json") as f:
        httpx_mock.add_response(
            url="https://osu.ppy.sh/api/get_beatmaps?k=testing&s=1209473",
            json=json.load(f),
        )

    with open("tests/data/aiess/first.json") as f:
        events = json.load(f)
        for event in events:
            res = client.post(
                "/qat/aiess", headers={"Authorization": "testing"}, json=event
            )
            assert res.status_code == 200

    Reset.filter(userId=1).get()
    Nomination.filter(userId=1).get()


def test_error(client: TestClient, httpx_mock: HTTPXMock):
    routine.USE_INTEROP = False
    qat.QAT_KEY = "testing"

    httpx_mock.add_response(
        url="https://bn.mappersguild.com/users/relevantInfo", data="nope"
    )

    with open("tests/data/aiess/error.json") as f:
        res = client.post(
            "/qat/aiess", headers={"Authorization": "testing"}, json=json.load(f)
        )
        assert res.status_code == 500
        assert res.json() == {
            "status": 500,
            "messages": "Cannot find user in database, maybe pishi site is falling behind?",
        }
