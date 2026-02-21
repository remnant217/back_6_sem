import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def test_check_connect(client: TestClient):
    response = client.get("/utils/check-db")
    print(response.text)
    assert response.status_code == 200


def test_get_id(client: TestClient):
    headers = {
        "Accept": "application/json"
    }
    res = client.get("/users/b7b108bc-6a46-4f94-9777-5609bf2f15a6", headers=headers)
    print(res.text)
    assert res.status_code == 200