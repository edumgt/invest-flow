from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..security import require_auth

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class EventBody(BaseModel):
    title: str | None = None
    event_type: str = "general"
    ticker: str | None = None
    start: str | None = None
    end: str | None = None
    notes: str | None = None
    is_ai_recommended: bool = False
    priority: str = "MEDIUM"


@router.get("/events")
def list_events(payload: dict = Depends(require_auth)):
    try:
        with db.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, title, event_type, ticker, start_at, end_at,
                       notes, is_ai_recommended, priority, status
                FROM investment_events
                WHERE user_id = %s
                ORDER BY start_at;
                """,
                (payload["sub"],),
            )
            rows = cur.fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="캘린더 이벤트 조회 실패")

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "event_type": r["event_type"],
            "ticker": r["ticker"],
            "start": r["start_at"].isoformat(),
            "end": r["end_at"].isoformat(),
            "notes": r["notes"],
            "is_ai_recommended": r["is_ai_recommended"],
            "priority": r["priority"],
            "status": r["status"],
        }
        for r in rows
    ]


@router.post("/events", status_code=201)
def add_event(body: EventBody, payload: dict = Depends(require_auth)):
    if not body.title or not body.start or not body.end:
        raise HTTPException(status_code=400, detail="title, start, end는 필수입니다.")

    try:
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO investment_events
                  (user_id, title, event_type, ticker, start_at, end_at, notes, is_ai_recommended, priority)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (payload["sub"], body.title, body.event_type, body.ticker or "",
                 body.start, body.end, body.notes or "", body.is_ai_recommended, body.priority),
            )
            row = cur.fetchone()
    except Exception:
        raise HTTPException(status_code=500, detail="이벤트 추가 실패")

    return {"id": row["id"]}


@router.delete("/events/{event_id}")
def delete_event(event_id: int, payload: dict = Depends(require_auth)):
    try:
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM investment_events WHERE id = %s AND user_id = %s;",
                (event_id, payload["sub"]),
            )
    except Exception:
        raise HTTPException(status_code=500, detail="삭제 실패")

    return {"message": "삭제 완료"}
