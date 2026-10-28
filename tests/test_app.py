from pathlib import Path

# The application database is defined at import time; tests use the app's default database.
from fastapi.testclient import TestClient
from main import app

def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_homepage():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "AccessResQ" in response.text

def test_reports_and_metrics():
    with TestClient(app) as client:
        reports = client.get("/api/reports")
        assert reports.status_code == 200
        assert isinstance(reports.json(), list)
        metrics = client.get("/api/metrics")
        assert metrics.status_code == 200
        assert "pending_verification" in metrics.json()

def test_create_report():
    with TestClient(app) as client:
        payload = {
            "title": "Test water request",
            "category": "water",
            "description": "Test-only report for automated API validation.",
            "area": "Test area",
            "lat": 4.711,
            "lng": -74.072,
            "quantity_needed": 10,
            "quantity_delivered": 0,
            "people_affected": 5,
            "source": "Automated test"
        }
        response = client.post("/api/reports", json=payload)
        assert response.status_code == 201
        assert response.json()["verification"] == "pending"


def test_invalid_category_is_rejected():
    with TestClient(app) as client:
        payload = {
            "title": "Test invalid category",
            "category": "not-a-category",
            "description": "Test-only report for validation checks.",
            "area": "Test area",
            "lat": 4.711,
            "lng": -74.072,
            "quantity_needed": 10,
            "quantity_delivered": 0,
            "people_affected": 5,
        }
        response = client.post("/api/reports", json=payload)
        assert response.status_code == 422


def test_status_update_unknown_report_returns_404(monkeypatch):
    import main
    monkeypatch.setattr(main, "ADMIN_TOKEN", "test-secret-token")
    with TestClient(app) as client:
        response = client.patch(
            "/api/reports/99999999/status",
            headers={"X-Admin-Token": "test-secret-token"},
            json={"status": "in_progress", "verification": "verified"},
        )
        assert response.status_code == 404


def test_frontend_captures_form_before_await():
    app_js = Path(__file__).resolve().parents[1] / "static" / "app.js"
    source = app_js.read_text(encoding="utf-8")
    assert "const reportForm = event.currentTarget;" in source
    assert "reportForm.reset();" in source
    assert "event.currentTarget.reset();" not in source


def test_status_update_requires_server_token(monkeypatch):
    import main
    monkeypatch.setattr(main, "ADMIN_TOKEN", "")
    with TestClient(app) as client:
        response = client.patch(
            "/api/reports/1/status",
            json={"status": "in_progress", "verification": "verified"},
        )
        assert response.status_code == 503


def test_status_update_rejects_wrong_token(monkeypatch):
    import main
    monkeypatch.setattr(main, "ADMIN_TOKEN", "test-secret-token")
    with TestClient(app) as client:
        response = client.patch(
            "/api/reports/1/status",
            headers={"X-Admin-Token": "wrong-token"},
            json={"status": "in_progress", "verification": "verified"},
        )
        assert response.status_code == 401


def test_status_update_accepts_configured_token(monkeypatch):
    import main
    monkeypatch.setattr(main, "ADMIN_TOKEN", "test-secret-token")
    with TestClient(app) as client:
        reports = client.get("/api/reports").json()
        report_id = reports[0]["id"]
        response = client.patch(
            f"/api/reports/{report_id}/status",
            headers={"X-Admin-Token": "test-secret-token"},
            json={"status": "in_progress", "verification": "verified"},
        )
        assert response.status_code == 200
        assert response.json()["verification"] == "verified"
