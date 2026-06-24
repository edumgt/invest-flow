// Ollama HTTP 스트리밍 API 기반 AI 추천 모듈
// stream: true 로 토큰별 진행 상황을 SSE progress 콜백으로 전달한다.

const OLLAMA_URL   = process.env.OLLAMA_URL   || 'http://172.29.32.1:11300';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'qwen3.5:latest';

// ── 날짜 유틸 ────────────────────────────────────────────────────────────────

const TODAY = () => new Date().toISOString().split('T')[0];

// ── 프롬프트 빌더 ────────────────────────────────────────────────────────────

function buildPrompts(portfolio) {
  const today = TODAY();
  const portfolioText = portfolio.length
    ? portfolio.map(
        (p) => `- ${p.asset_name}(${p.ticker}): ${p.quantity}주 × 평균단가 ${p.avg_price.toLocaleString()} ${p.currency}`,
      ).join('\n')
    : '(포트폴리오 없음 — 일반적인 투자 추천 5개를 제공하세요)';

  const systemPrompt =
    '투자 일정 추천 전문가입니다. 요청된 JSON 형식으로만 응답합니다. ' +
    '마크다운 코드블록, <think> 태그, 부가 설명 없이 순수 JSON만 출력하세요.';

  const userPrompt = `당신은 한국의 개인 투자 비서 AI입니다. 사용자의 포트폴리오를 분석하고 향후 투자 일정 5개를 제안하세요.

오늘 날짜: ${today}

[사용자 포트폴리오]
${portfolioText}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "recommendations": [
    {
      "ticker": "종목코드",
      "asset_name": "자산명 (한국어)",
      "action": "BUY 또는 SELL 또는 REBALANCE 또는 WATCH",
      "category": "매수 또는 매도 또는 리밸런싱 또는 실적확인 또는 배당",
      "reason": "추천 이유 (한국어, 2-3문장, 구체적 근거 포함)",
      "suggested_date": "YYYY-MM-DD (오늘로부터 3~60일 이내 평일)",
      "priority": "HIGH 또는 MEDIUM 또는 LOW"
    }
  ]
}

규칙:
- 반드시 5개의 추천을 생성하세요
- 실제 시장 논리에 기반한 현실적인 추천을 하세요
- 포트폴리오에 없는 종목도 추천할 수 있습니다`;

  return { systemPrompt, userPrompt };
}

// ── JSON 추출 ────────────────────────────────────────────────────────────────

function extractJson(raw) {
  // ① thinking 모델의 <think>...</think> 블록 제거
  let cleaned = raw.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  // ② 마크다운 코드블록 ```json ... ``` 제거
  cleaned = cleaned.replace(/```(?:json)?\s*([\s\S]*?)```/g, '$1').trim();
  // ③ 첫 번째 { ... } JSON 객체 추출
  const m = cleaned.match(/\{[\s\S]*\}/);
  if (!m) throw new Error('AI 응답에서 JSON을 찾을 수 없습니다');
  const result = JSON.parse(m[0]);
  if (!Array.isArray(result.recommendations)) throw new Error('잘못된 응답 형식');
  return result;
}

// ── 스트리밍 추천 생성 (SSE 진행 콜백 포함) ──────────────────────────────────
//
// sendProgress({ type, message, percent }) 콜백으로 SSE 이벤트를 발행한다.
// Ollama stream: true 모드로 토큰을 받으면서 실시간 진행률을 계산한다.
// 추천 완성 시 result 객체를 반환한다.
// 오류 시 Error를 throw — 목업 없이 호출자가 처리한다.
export async function generateRecommendationsStream(portfolio, sendProgress) {
  const { systemPrompt, userPrompt } = buildPrompts(portfolio);

  sendProgress({ type: 'progress', message: 'GPU 모델 초기화 중...', percent: 12 });

  // 10분 타임아웃 (대형 모델 최초 로드 포함)
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10 * 60 * 1000);

  try {
    const res = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model:   OLLAMA_MODEL,
        stream:  true,           // 토큰 단위 스트리밍 — 진행률 계산 가능
        think:   false,          // qwen3.5 reasoning 블록 비활성화 → 순수 JSON 출력
        options: { temperature: 0.3 },
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user',   content: userPrompt  },
        ],
      }),
    });

    if (!res.ok) throw new Error(`Ollama HTTP ${res.status}: ${await res.text()}`);

    sendProgress({ type: 'progress', message: 'AI GPU 추론 시작...', percent: 15 });

    // 응답 바디를 청크 단위로 읽으며 토큰을 누적
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer       = '';
    let fullContent  = '';
    let tokenCount   = 0;
    // 예상 토큰 수: qwen3.5가 투자 추천 5개 생성 시 약 600~800 토큰
    const EST_TOKENS = 700;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // 마지막 미완성 라인은 다음 청크까지 보류

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const obj = JSON.parse(line);
          if (obj.message?.content) {
            fullContent += obj.message.content;
            tokenCount++;
            // 10토큰마다 한 번씩 progress 전송 (SSE 이벤트 과부하 방지)
            if (tokenCount % 10 === 0) {
              const pct = Math.min(15 + Math.floor((tokenCount / EST_TOKENS) * 79), 94);
              sendProgress({
                type: 'progress',
                message: `GPU 추론 중... (${tokenCount} 토큰 생성됨)`,
                percent: pct,
              });
            }
          }
        } catch { /* 파싱 실패한 라인은 무시 */ }
      }
    }

    sendProgress({ type: 'progress', message: '응답 분석 중...', percent: 96 });

    return extractJson(fullContent);

  } finally {
    clearTimeout(timer);
  }
}

// ── 비스트리밍 래퍼 (기존 POST 엔드포인트 호환용) ─────────────────────────────
// sendProgress 없이 호출 가능하도록 진행 이벤트를 console.log로 대체한다.
export async function generateRecommendations(portfolio) {
  return generateRecommendationsStream(portfolio, (e) => {
    if (e.type === 'progress') console.log(`[AI] ${e.percent}% ${e.message}`);
  });
}
