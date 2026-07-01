import json

import httpx
import pytest
import respx

from app import config
from app.services import ai_service


def test_extract_json_strips_think_and_code_fence():
    raw = (
        "<think>내부 추론 과정...</think>\n"
        "```json\n"
        '{"recommendations": [{"ticker": "AAPL"}]}\n'
        "```"
    )
    result = ai_service._extract_json(raw)
    assert result["recommendations"] == [{"ticker": "AAPL"}]


def test_extract_json_no_json_raises():
    with pytest.raises(ValueError):
        ai_service._extract_json("이건 JSON이 아닙니다")


def test_extract_json_wrong_shape_raises():
    with pytest.raises(ValueError):
        ai_service._extract_json('{"recommendations": "not-a-list"}')


async def test_generate_recommendations_stream_success(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_URL", "http://fake-ollama")
    lines = [
        {"message": {"content": '{"recommendations":[{"ticker":"AAPL",'}},
        {"message": {"content": '"asset_name":"Apple","action":"BUY","category":"매수",'}},
        {"message": {"content": '"reason":"r","suggested_date":"2026-07-10","priority":"HIGH"}]}'}},
    ]
    body = "\n".join(json.dumps(line) for line in lines) + "\n"

    events = []

    async def send(event):
        events.append(event)

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://fake-ollama/api/chat").mock(return_value=httpx.Response(200, content=body.encode()))
        result = await ai_service.generate_recommendations_stream([], send)

    assert result["recommendations"][0]["ticker"] == "AAPL"
    assert any(e["type"] == "progress" for e in events)


async def test_generate_recommendations_stream_ollama_http_error(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_URL", "http://fake-ollama")

    async def send(event):
        pass

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://fake-ollama/api/chat").mock(return_value=httpx.Response(500, content=b"boom"))
        with pytest.raises(RuntimeError, match="Ollama HTTP 500"):
            await ai_service.generate_recommendations_stream([], send)


async def test_generate_recommendations_stream_connection_error(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_URL", "http://fake-ollama")

    async def send(event):
        pass

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://fake-ollama/api/chat").mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(httpx.ConnectError):
            await ai_service.generate_recommendations_stream([], send)
