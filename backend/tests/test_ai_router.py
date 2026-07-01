import json

from app.routers import ai as ai_router


def _parse_sse(text: str) -> list[dict]:
    events = []
    for chunk in text.split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[len("data: "):]))
    return events


def test_recommend_stream_requires_auth(client):
    res = client.post("/api/ai/recommend/stream")
    assert res.status_code == 401


def test_recommend_stream_success(auth_client, fake_db, monkeypatch):
    fake_db.queue_fetchall([
        {"ticker": "AAPL", "asset_name": "Apple", "asset_type": "stock",
         "quantity": 8, "avg_price": 182.0, "currency": "USD"},
    ])

    async def fake_stream(portfolio, send):
        assert portfolio[0]["ticker"] == "AAPL"
        await send({"type": "progress", "message": "추론 중...", "percent": 50})
        return {"recommendations": [{"ticker": "AAPL", "action": "BUY"}]}

    monkeypatch.setattr(ai_router, "generate_recommendations_stream", fake_stream)

    with auth_client.stream("POST", "/api/ai/recommend/stream") as res:
        text = "".join(res.iter_text())

    events = _parse_sse(text)
    types = [e["type"] for e in events]
    assert types == ["progress", "progress", "progress", "done"]
    assert events[-1]["recommendations"] == [{"ticker": "AAPL", "action": "BUY"}]


def test_recommend_stream_propagates_error_as_sse_event(auth_client, fake_db, monkeypatch):
    fake_db.queue_fetchall([])

    async def failing_stream(portfolio, send):
        raise RuntimeError("Ollama 연결 실패")

    monkeypatch.setattr(ai_router, "generate_recommendations_stream", failing_stream)

    with auth_client.stream("POST", "/api/ai/recommend/stream") as res:
        text = "".join(res.iter_text())

    events = _parse_sse(text)
    assert events[-1] == {"type": "error", "message": "Ollama 연결 실패"}
