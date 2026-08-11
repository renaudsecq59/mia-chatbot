"""Tests du health check et endpoints de base."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_health():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_llms_txt():
    r = client.get("/llms.txt")
    assert r.status_code == 200
    assert "MIA Veille" in r.text
