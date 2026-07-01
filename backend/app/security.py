from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config

_bearer = HTTPBearer(auto_error=False)


def sign_jwt(sub: int, username: str, display_name: str) -> str:
    payload = {
        # PyJWT는 "sub" 클레임이 문자열일 것을 강제한다 (RFC 7519) — decode 시 다시 int로 변환한다.
        "sub": str(sub),
        "username": username,
        "displayName": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def verify_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    payload["sub"] = int(payload["sub"])
    return payload


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    payload = verify_jwt(credentials.credentials) if credentials else None
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")
    return payload
