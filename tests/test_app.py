from fastapi.testclient import TestClient
import main


def make_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(main, "SECRET_KEY", "test-secret-key-long-enough-for-tests")
    monkeypatch.setattr(main, "ADMIN_TOKEN", "test-reviewer-token")
    return TestClient(main.app)


def test_health_and_demo_records(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        reports = client.get("/api/reports").json()
        assert len(reports) >= 3
        assert all("contact" not in report for report in reports)
        assert any(report["verification"] == "sample" for report in reports)


def test_report_submission_and_validation(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        payload = {
            "title": "Need drinking water", "category": "water", "urgency": "critical",
            "description": "Several households need clean drinking water.", "area": "Test area, Sylhet",
            "lat": 24.8949, "lng": 91.8687, "people_affected": 8, "children_count": 2,
            "mobility_support": 1, "needs": "Water and dry food", "contact": "0123456789"
        }
        response = client.post("/api/reports", json=payload)
        assert response.status_code == 201
        report = response.json()
        assert report["public_id"].startswith("AR-")
        assert report["status"] == "needed"
        assert "contact" not in report
        assert client.post("/api/reports", json={**payload, "lat": 10}).status_code == 422


def test_auth_and_private_documents(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/documents").status_code == 401
        reg = client.post("/api/auth/register", json={
            "name": "Demo User", "email": "demo@example.com", "phone": "", "password": "safe-password-123"
        })
        assert reg.status_code == 201
        assert client.get("/api/me").json()["authenticated"] is True
        pdf = b"%PDF-1.4\n% test document\n%%EOF"
        upload = client.post("/api/documents", files={"file": ("certificate.pdf", pdf, "application/pdf")})
        assert upload.status_code == 201, upload.text
        public_id = upload.json()["public_id"]
        assert len(client.get("/api/documents").json()) == 1
        download = client.get(f"/api/documents/{public_id}/download")
        assert download.status_code == 200
        assert download.content == pdf
        client.post("/api/auth/logout")
        assert client.get(f"/api/documents/{public_id}/download").status_code == 401
        assert client.post("/api/auth/login", json={"email": "demo@example.com", "password": "wrong-password"}).status_code == 401


def test_shelters_are_not_falsely_claimed_verified(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/shelters?verified_only=true").json() == []
        assert client.post("/api/shelters", headers={"X-Admin-Token": "test-reviewer-token"}, json={
            "name": "Community Shelter", "address": "Test address", "lat": 24.9, "lng": 91.8, "contact": "", "source": "Local authority"
        }).status_code == 201
        assert client.get("/api/shelters?verified_only=true").json() == []
        assert client.get("/api/shelters").json()[0]["verification"] == "pending"
