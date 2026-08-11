"""Tests de l'endpoint livre blanc — validation des champs obligatoires."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _mock_db(monkeypatch):
    """Mock Firestore pour éviter d'écrire en production pendant les tests."""
    class FakeDoc:
        def set(self, data, merge=False):
            return None

    class FakeCollection:
        def document(self, _id):
            return FakeDoc()

    class FakeDB:
        def collection(self, _name):
            return FakeCollection()

    monkeypatch.setattr("main.db", FakeDB())


def test_livre_blanc_champs_manquants():
    """Tous les champs sont obligatoires — doit échouer si un manque."""
    payload = {"first_name": "Jean", "last_name": "Dupont", "company": "", "email": "jean@test.com"}
    r = client.post("/api/livre-blanc/download", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False


def test_livre_blanc_email_invalide():
    """Email invalide — doit être rejeté."""
    payload = {"first_name": "Jean", "last_name": "Dupont", "company": "TestCo", "email": "pas-un-email"}
    r = client.post("/api/livre-blanc/download", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "invalide" in data["message"].lower()


def test_livre_blanc_succes():
    """Tous les champs valides — doit retourner l'URL du PDF."""
    payload = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "company": "TestCo",
        "email": "jean.dupont@test.com",
        "newsletter": True,
    }
    r = client.post("/api/livre-blanc/download", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["download_url"].endswith(".pdf")


def test_livre_blanc_sans_newsletter():
    """Opt-in newsletter est optionnel — doit marcher sans."""
    payload = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "company": "TestCo",
        "email": "jean.dupont@test.com",
        "newsletter": False,
    }
    r = client.post("/api/livre-blanc/download", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_livre_blanc_newsletter_default_false():
    """Si newsletter non fourni, défaut = False."""
    payload = {"first_name": "Jean", "last_name": "Dupont", "company": "TestCo", "email": "jean@test.com"}
    r = client.post("/api/livre-blanc/download", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
