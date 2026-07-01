from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..security import require_auth

router = APIRouter(prefix="/api/investments", tags=["investments"])


class InvestmentBody(BaseModel):
    ticker: str | None = None
    asset_name: str | None = None
    asset_type: str = "stock"
    quantity: float | None = None
    avg_price: float | None = None
    currency: str = "KRW"


@router.get("")
def list_investments(payload: dict = Depends(require_auth)):
    try:
        with db.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, asset_name, asset_type, quantity, avg_price, currency
                FROM investments WHERE user_id = %s ORDER BY created_at;
                """,
                (payload["sub"],),
            )
            rows = cur.fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="포트폴리오 조회 실패")

    return [
        {
            "id": r["id"],
            "ticker": r["ticker"],
            "asset_name": r["asset_name"],
            "asset_type": r["asset_type"],
            "quantity": float(r["quantity"]),
            "avg_price": float(r["avg_price"]),
            "currency": r["currency"],
        }
        for r in rows
    ]


@router.post("", status_code=201)
def add_investment(body: InvestmentBody, payload: dict = Depends(require_auth)):
    if not body.ticker or not body.asset_name or body.quantity is None or body.avg_price is None:
        raise HTTPException(status_code=400, detail="ticker, asset_name, quantity, avg_price는 필수입니다.")

    try:
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO investments (user_id, ticker, asset_name, asset_type, quantity, avg_price, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (payload["sub"], body.ticker, body.asset_name, body.asset_type,
                 body.quantity, body.avg_price, body.currency),
            )
            row = cur.fetchone()
    except Exception:
        raise HTTPException(status_code=500, detail="포트폴리오 추가 실패")

    return {"id": row["id"]}


@router.delete("/{investment_id}")
def delete_investment(investment_id: int, payload: dict = Depends(require_auth)):
    try:
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM investments WHERE id = %s AND user_id = %s;",
                (investment_id, payload["sub"]),
            )
    except Exception:
        raise HTTPException(status_code=500, detail="삭제 실패")

    return {"message": "삭제 완료"}
