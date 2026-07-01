from app.security import verify_jwt


def test_login_success(client, fake_db):
    fake_db.queue_fetchone({"id": 2, "username": "alice", "display_name": "Alice Kim"})

    res = client.post("/api/auth/login", json={"username": "alice", "password": "Passw0rd!"})

    assert res.status_code == 200
    body = res.json()
    assert body["user"] == {"id": 2, "username": "alice", "displayName": "Alice Kim"}
    payload = verify_jwt(body["token"])
    assert payload["sub"] == 2
    assert payload["username"] == "alice"


def test_login_missing_fields(client):
    res = client.post("/api/auth/login", json={"username": "alice"})
    assert res.status_code == 400
    assert res.json()["message"] == "username과 password는 필수입니다."


def test_login_wrong_credentials(client, fake_db):
    fake_db.queue_fetchone(None)
    res = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert res.status_code == 401
    assert "아이디" in res.json()["message"]


def test_login_db_error(client, fake_db):
    fake_db.raise_error = RuntimeError("connection refused")
    res = client.post("/api/auth/login", json={"username": "alice", "password": "x"})
    assert res.status_code == 500
    assert res.json()["message"] == "로그인 처리 중 오류가 발생했습니다."
