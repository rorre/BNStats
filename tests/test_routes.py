from bs4 import BeautifulSoup
from starlette.testclient import TestClient

from bnstats.score import NaxessCalculator


def test_homepage(client: TestClient):
    assert client.get("/").status_code == 200


def test_user_listing(client: TestClient):
    res = client.get("/users/")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    assert len(soup.select("tbody > tr")) == 1


def test_user_profile(client: TestClient):
    client.app.state.calc_system = NaxessCalculator()
    res = client.get("/users/1")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".ui.large.relaxed.divided.inverted.list > .item")

    assert "3" in str(items[1])
    assert "3:13" in str(items[2])
    print(str(items[3]))
    assert "3.08" in str(items[3])


def test_user_404(client: TestClient):
    res = client.get("/users/2")
    assert res.status_code == 404


def test_user_score(client: TestClient):
    res = client.get("/score/1")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    assert len(soup.select("tbody > tr")) == 2


def test_user_score_404(client: TestClient):
    res = client.get("/score/2")
    assert res.status_code == 404
