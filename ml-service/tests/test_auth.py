"""API-key auth tests — configured, missing, and local-dev opt-in paths."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FEATURES = {
    "progress_pct": 50, "days_since_last_login": 3,
    "quiz_avg": 70, "lessons_per_week": 2, "chat_messages": 4,
}


class TestConfiguredKey:
    def test_missing_header_is_401(self, monkeypatch):
        monkeypatch.setenv("ML_API_KEY", "sekret")
        res = client.post("/v1/predict/dropout-risk", json=FEATURES)
        assert res.status_code == 401

    def test_wrong_key_is_401(self, monkeypatch):
        monkeypatch.setenv("ML_API_KEY", "sekret")
        res = client.post(
            "/v1/predict/dropout-risk", json=FEATURES,
            headers={"X-API-Key": "wrong"},
        )
        assert res.status_code == 401

    def test_correct_key_succeeds(self, monkeypatch):
        monkeypatch.setenv("ML_API_KEY", "sekret")
        res = client.post(
            "/v1/predict/dropout-risk", json=FEATURES,
            headers={"X-API-Key": "sekret"},
        )
        assert res.status_code == 200
        assert "probability" in res.json()

    def test_pipeline_routes_require_key_too(self, monkeypatch):
        monkeypatch.setenv("ML_API_KEY", "sekret")
        res = client.get("/api/pipeline/dataset")
        assert res.status_code == 401


class TestUnsetKey:
    def test_unset_key_fails_closed_with_503(self, monkeypatch):
        monkeypatch.delenv("ML_API_KEY", raising=False)
        monkeypatch.delenv("ML_ALLOW_UNAUTHENTICATED", raising=False)
        res = client.post("/v1/predict/dropout-risk", json=FEATURES)
        assert res.status_code == 503
        assert "ML_API_KEY not configured" in res.json()["detail"]

    def test_explicit_local_dev_opt_in(self, monkeypatch):
        monkeypatch.delenv("ML_API_KEY", raising=False)
        monkeypatch.setenv("ML_ALLOW_UNAUTHENTICATED", "1")
        res = client.post("/v1/predict/dropout-risk", json=FEATURES)
        assert res.status_code == 200


class TestExemptRoutes:
    """Health, model listing and metrics stay open for orchestration/scrapes."""

    def test_open_even_when_key_configured(self, monkeypatch):
        monkeypatch.setenv("ML_API_KEY", "sekret")
        assert client.get("/healthz").status_code == 200
        assert client.get("/v1/models").status_code == 200
        assert client.get("/metrics").status_code == 200

    def test_open_even_when_key_unset(self, monkeypatch):
        monkeypatch.delenv("ML_API_KEY", raising=False)
        monkeypatch.delenv("ML_ALLOW_UNAUTHENTICATED", raising=False)
        assert client.get("/healthz").status_code == 200
        assert client.get("/v1/models").status_code == 200
        assert client.get("/metrics").status_code == 200
