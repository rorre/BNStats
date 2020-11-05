from bs4 import BeautifulSoup
from starlette.testclient import TestClient


def test_homepage(client_without_middleware: TestClient):
    assert client_without_middleware.get("/").status_code == 200


def test_user_listing(client_without_middleware: TestClient):
    res = client_without_middleware.get("/users/")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    assert len(soup.select("tbody > tr")) == 1


def test_user_profile(client_without_middleware: TestClient):
    res = client_without_middleware.get("/users/1")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".ui.large.relaxed.divided.inverted.list > .item")

    assert "3" in str(items[1])
    assert "3:13" in str(items[2])
    assert "3.53" in str(items[3])


def test_user_404(client_without_middleware: TestClient):
    res = client_without_middleware.get("/users/2")
    assert res.status_code == 404


def test_user_score(client_without_middleware: TestClient):
    res = client_without_middleware.get("/score/1")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    assert len(soup.select("tbody > tr")) == 2


def test_user_score_404(client_without_middleware: TestClient):
    res = client_without_middleware.get("/score/2")
    assert res.status_code == 404
