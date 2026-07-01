from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..security import sign_jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str | None = None
    password: str | None = None


@router.post("/login")
def login(body: LoginBody):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username과 password는 필수입니다.")

    try:
        with db.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, username, display_name FROM users
                WHERE username = %s
                  AND password_hash = crypt(%s, password_hash)
                LIMIT 1;
                """,
                (body.username, body.password),
            )
            row = cur.fetchone()
    except Exception:
        raise HTTPException(status_code=500, detail="로그인 처리 중 오류가 발생했습니다.")

    if not row:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = sign_jwt(row["id"], row["username"], row["display_name"])
    return {
        "token": token,
        "user": {"id": row["id"], "username": row["username"], "displayName": row["display_name"]},
    }
