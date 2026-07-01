import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .. import db
from ..security import require_auth
from ..services.ai_service import generate_recommendations, generate_recommendations_stream

router = APIRouter(prefix="/api/ai", tags=["ai"])

_DONE = object()


def _load_portfolio(user_id: int) -> list[dict]:
    with db.get_cursor() as cur:
        cur.execute(
            """
            SELECT ticker, asset_name, asset_type, quantity, avg_price, currency
            FROM investments WHERE user_id = %s ORDER BY created_at;
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "ticker": r["ticker"],
            "asset_name": r["asset_name"],
            "asset_type": r["asset_type"],
            "quantity": float(r["quantity"]),
            "avg_price": float(r["avg_price"]),
            "currency": r["currency"],
        }
        for r in rows
    ]


@router.post("/recommend/stream")
async def recommend_stream(payload: dict = Depends(require_auth)):
    queue: asyncio.Queue = asyncio.Queue()

    async def send(data: dict) -> None:
        await queue.put(data)

    async def process() -> None:
        try:
            await send({"type": "progress", "message": "포트폴리오 로딩 중...", "percent": 3})
            portfolio = await asyncio.to_thread(_load_portfolio, payload["sub"])
            await send({"type": "progress", "message": f"포트폴리오 {len(portfolio)}개 종목 확인", "percent": 8})

            data = await generate_recommendations_stream(portfolio, send)

            await send({"type": "done", "recommendations": data["recommendations"]})
        except Exception as err:
            await send({"type": "error", "message": str(err)})
        finally:
            await queue.put(_DONE)

    async def event_generator():
        task = asyncio.create_task(process())
        try:
            while True:
                item = await queue.get()
                if item is _DONE:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        finally:
            await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/recommend")
async def recommend(payload: dict = Depends(require_auth)):
    try:
        portfolio = await asyncio.to_thread(_load_portfolio, payload["sub"])
        return await generate_recommendations(portfolio)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"AI 추천 생성 실패: {err}")
