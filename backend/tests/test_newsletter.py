"""Tests de l'endpoint newsletter — validation email."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _mock_db(monkeypatch):
    class FakeDoc:
        exists = False

        def get(self):
            return FakeDoc()

        def set(self, data, merge=False):
            return None

    class FakeCollection:
        def document(self, _id):
            return FakeDoc()

    class FakeDB:
        def collection(self, _name):
            return FakeCollection()

    monkeypatch.setattr("main.db", FakeDB())


def test_newsletter_email_invalide():
    r = client.post("/api/newsletter/subscribe", json={"email": "pas-valide"})
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_newsletter_succes():
    r = client.post("/api/newsletter/subscribe", json={"email": "test@example.com"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
