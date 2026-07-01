"""Ollama HTTP 스트리밍 API 기반 AI 추천 모듈.

stream=True 로 토큰별 진행 상황을 SSE progress 콜백으로 전달한다.
"""
import json
import re
from datetime import date
from typing import Awaitable, Callable

import httpx

from .. import config

ProgressCallback = Callable[[dict], Awaitable[None]]


def _build_prompts(portfolio: list[dict]) -> tuple[str, str]:
    today = date.today().isoformat()
    if portfolio:
        portfolio_text = "\n".join(
            f"- {p['asset_name']}({p['ticker']}): {p['quantity']}주 × 평균단가 {p['avg_price']:,} {p['currency']}"
            for p in portfolio
        )
    else:
        portfolio_text = "(포트폴리오 없음 — 일반적인 투자 추천 5개를 제공하세요)"

    system_prompt = (
        "투자 일정 추천 전문가입니다. 요청된 JSON 형식으로만 응답합니다. "
        "마크다운 코드블록, <think> 태그, 부가 설명 없이 순수 JSON만 출력하세요."
    )

    user_prompt = f"""당신은 한국의 개인 투자 비서 AI입니다. 사용자의 포트폴리오를 분석하고 향후 투자 일정 5개를 제안하세요.

오늘 날짜: {today}

[사용자 포트폴리오]
{portfolio_text}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "recommendations": [
    {{
      "ticker": "종목코드",
      "asset_name": "자산명 (한국어)",
      "action": "BUY 또는 SELL 또는 REBALANCE 또는 WATCH",
      "category": "매수 또는 매도 또는 리밸런싱 또는 실적확인 또는 배당",
      "reason": "추천 이유 (한국어, 2-3문장, 구체적 근거 포함)",
      "suggested_date": "YYYY-MM-DD (오늘로부터 3~60일 이내 평일)",
      "priority": "HIGH 또는 MEDIUM 또는 LOW"
    }}
  ]
}}

규칙:
- 반드시 5개의 추천을 생성하세요
- 실제 시장 논리에 기반한 현실적인 추천을 하세요
- 포트폴리오에 없는 종목도 추천할 수 있습니다"""

    return system_prompt, user_prompt


def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw).strip()
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", cleaned).strip()
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if not m:
        raise ValueError("AI 응답에서 JSON을 찾을 수 없습니다")
    result = json.loads(m.group())
    if not isinstance(result.get("recommendations"), list):
        raise ValueError("잘못된 응답 형식")
    return result


async def generate_recommendations_stream(portfolio: list[dict], send_progress: ProgressCallback) -> dict:
    system_prompt, user_prompt = _build_prompts(portfolio)

    await send_progress({"type": "progress", "message": "GPU 모델 초기화 중...", "percent": 12})

    full_content = ""
    token_count = 0
    est_tokens = 700  # qwen3.5가 투자 추천 5개 생성 시 약 600~800 토큰

    timeout = httpx.Timeout(10 * 60.0)  # 10분 타임아웃 (대형 모델 최초 로드 포함)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "stream": True,
                "think": False,
                "options": {"temperature": 0.3},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        ) as res:
            if res.status_code != 200:
                body = await res.aread()
                raise RuntimeError(f"Ollama HTTP {res.status_code}: {body.decode(errors='replace')}")

            await send_progress({"type": "progress", "message": "AI GPU 추론 시작...", "percent": 15})

            async for line in res.aiter_lines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = obj.get("message", {}).get("content")
                if content:
                    full_content += content
                    token_count += 1
                    if token_count % 10 == 0:
                        pct = min(15 + int((token_count / est_tokens) * 79), 94)
                        await send_progress({
                            "type": "progress",
                            "message": f"GPU 추론 중... ({token_count} 토큰 생성됨)",
                            "percent": pct,
                        })

    await send_progress({"type": "progress", "message": "응답 분석 중...", "percent": 96})

    return _extract_json(full_content)


async def generate_recommendations(portfolio: list[dict]) -> dict:
    async def _log_progress(event: dict) -> None:
        if event.get("type") == "progress":
            print(f"[AI] {event.get('percent')}% {event.get('message')}")

    return await generate_recommendations_stream(portfolio, _log_progress)
