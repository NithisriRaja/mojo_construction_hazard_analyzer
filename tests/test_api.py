"""
API tests that never call Claude (no cost). The Claude HTTP call
(claude_client._create) is replaced by a fake that returns canned responses,
so the real analyzer, schema validation, message, usage logging and cost
headers are all exercised. The usage log is redirected to a temp folder.

Run:  venv\\Scripts\\python -m pytest tests -q
"""
import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from construction_hazards import claude_client, config, domo_client, usage_log

DRAFT = {"hazards": [
    {"title": "Cord across walkway", "description": "An orange cord crosses the aisle.", "severity": "Medium", "category": "Slips, Trips, and Falls"},
    {"title": "Unguarded floor opening", "description": "A floor opening has no guardrail.", "severity": "High", "category": "Working at Heights and Fall Protection"},
]}


def _fake_response(text: str, inp: int, out: int):
    return SimpleNamespace(
        model="claude-opus-5-5",
        stop_reason="end_turn",
        stop_details=None,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=inp, output_tokens=out, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


@pytest.fixture
def client(monkeypatch, tmp_path):
    calls = []

    def fake_create(path, media_type, prompt, system, model, output_config):
        calls.append(output_config)
        return _fake_response(json.dumps(DRAFT), 1000, 200)  # detect and verify both return DRAFT

    def fake_domo_post(payload):
        calls.append({"domo": payload["model"], "temperature": payload.get("temperature")})
        return {"output": json.dumps(DRAFT), "modelId": payload["model"],
                "modelProviderUsage": {"inputTokens": 900, "outputTokens": 150}}

    monkeypatch.setattr(claude_client, "_create", fake_create)
    monkeypatch.setattr(domo_client, "_post", fake_domo_post)
    monkeypatch.setattr(config, "CLAUDE_AVAILABLE", True)
    monkeypatch.setattr(config, "DOMO_AVAILABLE", True)
    monkeypatch.setattr(config, "DOMO_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(config, "DOMO_API_KEY", "test-token")
    monkeypatch.setattr(usage_log, "LOG_FILE", tmp_path / "api_usage.csv")
    monkeypatch.setattr(usage_log, "PENDING_FILE", tmp_path / "api_usage_pending.csv")
    c = TestClient(app)
    c.calls = calls
    c.log_file = tmp_path / "api_usage.csv"
    return c


def _png(size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok" and set(d["providers"]) == {"claude", "domo"}


def test_categories(client):
    d = client.get("/api/categories").json()
    assert len(d["categories"]) == 39
    assert d["severities"] == ["High", "Medium", "Low"]


def test_analyze_success(client):
    r = client.post("/api/analyze", files={"file": ("site photo.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert list(body) == ["message", "hazards"]
    assert body["message"] == "Here are 2 construction hazards I identified from the image"
    assert [h["severity"] for h in body["hazards"]] == ["High", "Medium"]  # sorted most severe first
    # 2 calls (detect + verify), no PPE claim -> no PPE check; structured output requested
    assert len(client.calls) == 2 and all("format" in oc for oc in client.calls)
    # usage headers: 2 x (1000 in, 200 out) at $4/$20 per 1M = 0.016
    assert r.headers["X-API-Calls"] == "2"
    assert r.headers["X-Input-Tokens"] == "2000"
    assert r.headers["X-Output-Tokens"] == "400"
    assert r.headers["X-Cost-USD"] == "0.016000"
    assert r.headers["X-Run-Id"].startswith("api-")
    rows = client.log_file.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 3 and "site photo.png" in rows[1] and r.headers["X-Run-Id"] in rows[1]


@pytest.mark.parametrize("name,data,status", [
    ("notes.txt", b"hello", 415),
    ("fake.png", b"not an image", 400),
    ("empty.png", b"", 400),
])
def test_analyze_rejects_bad_uploads(client, name, data, status):
    r = client.post("/api/analyze", files={"file": (name, data, "application/octet-stream")})
    assert r.status_code == status
    assert client.calls == []  # rejected before any (fake) Claude call


def test_upstream_failure_returns_502(client, monkeypatch):
    def broken(*a, **k):
        return _fake_response("not json", 10, 5)
    monkeypatch.setattr(claude_client, "_create", broken)
    monkeypatch.setattr("construction_hazards.config.MAX_ATTEMPTS", 1)
    r = client.post("/api/analyze", files={"file": ("x.png", _png(), "image/png")})
    assert r.status_code == 502


def test_analyze_domo(client):
    r = client.post("/api/analyze/domo", files={"file": ("site.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "Here are 2 construction hazards I identified from the image"
    assert len(client.calls) == 2 and all("domo" in c and c["temperature"] == 0 for c in client.calls)
    assert r.headers["X-Provider"] == "domo"
    assert r.headers["X-Input-Tokens"] == "1800" and r.headers["X-Output-Tokens"] == "300"
    assert r.headers["X-Cost-USD"] == "n/a"  # Domo bills through its own contract


def test_analyze_claude_alias(client):
    r = client.post("/api/analyze/claude", files={"file": ("site.png", _png(), "image/png")})
    assert r.status_code == 200 and r.headers["X-Provider"] == "claude"


def test_unconfigured_provider_returns_503(client, monkeypatch):
    monkeypatch.setattr(config, "DOMO_AVAILABLE", False)
    r = client.post("/api/analyze/domo", files={"file": ("site.png", _png(), "image/png")})
    assert r.status_code == 503
    assert client.calls == []


def test_domo_retries_without_temperature(client, monkeypatch):
    import requests
    seen = []

    def picky_post(payload):
        seen.append("temperature" in payload)
        if "temperature" in payload:
            resp = requests.Response(); resp.status_code = 400
            raise requests.HTTPError("temperature not supported", response=resp)
        return {"output": json.dumps(DRAFT), "modelProviderUsage": {"inputTokens": 10, "outputTokens": 5}}

    domo_client._NO_TEMPERATURE.clear()
    monkeypatch.setattr(domo_client, "_post", picky_post)
    r = client.post("/api/analyze/domo", files={"file": ("site.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    assert seen == [True, False, False]  # rejected once, then never sent again
    domo_client._NO_TEMPERATURE.clear()
