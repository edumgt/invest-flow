from app import db as db_module


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(db_module, "check_connection", lambda: None)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_db_error(client, monkeypatch):
    def _raise():
        raise RuntimeError("db down")

    monkeypatch.setattr(db_module, "check_connection", _raise)
    res = client.get("/health")
    assert res.status_code == 500
    assert res.json() == {"status": "db_error"}


def test_404_returns_message_field(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.json() == {"message": "Not Found"}
