from app.services import quality_service


def test_get_original_not_found(client, monkeypatch):
    monkeypatch.setattr(quality_service, "get_original", lambda: None)
    res = client.get("/api/quality/original")
    assert res.status_code == 404


def test_get_original_found_no_auth_required(client, monkeypatch):
    monkeypatch.setattr(quality_service, "get_original", lambda: {"base64": "abc", "mimeType": "image/avif"})
    res = client.get("/api/quality/original")
    assert res.status_code == 200
    assert res.json() == {"base64": "abc", "mimeType": "image/avif"}


def test_classify_requires_auth(client):
    res = client.post("/api/quality/classify", json={"base64": "abc"})
    assert res.status_code == 401


def test_classify_success(auth_client, monkeypatch):
    monkeypatch.setattr(
        quality_service, "classify_image",
        lambda b64, mime: {"result": "y", "label": "정품", "confidence": 0.9,
                            "reason": "ok", "sim_score": 0.95, "method": "similarity"},
    )
    res = auth_client.post("/api/quality/classify", json={"base64": "abc", "mimeType": "image/jpeg"})
    assert res.status_code == 200
    assert res.json()["result"] == "y"


def test_classify_missing_base64(auth_client):
    res = auth_client.post("/api/quality/classify", json={})
    assert res.status_code == 400
