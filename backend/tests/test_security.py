import jwt
import pytest

from app import config
from app.security import sign_jwt, verify_jwt


def test_sign_and_verify_roundtrip():
    token = sign_jwt(7, "alice", "Alice Kim")
    payload = verify_jwt(token)

    assert payload["sub"] == 7  # 문자열로 인코딩됐다가 int 로 복원되어야 함
    assert payload["username"] == "alice"
    assert payload["displayName"] == "Alice Kim"


def test_verify_rejects_bad_signature():
    token = sign_jwt(1, "alice", "Alice")
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    assert verify_jwt(tampered) is None


def test_verify_rejects_expired_token():
    import datetime

    payload = {
        "sub": "1",
        "username": "alice",
        "displayName": "Alice",
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    assert verify_jwt(expired_token) is None


def test_verify_rejects_wrong_secret():
    token = jwt.encode(
        {"sub": "1", "username": "alice", "displayName": "Alice"},
        "some-other-secret",
        algorithm="HS256",
    )
    assert verify_jwt(token) is None
