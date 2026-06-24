import http from 'node:http';
import crypto from 'node:crypto';
import { runQuery, sql } from './db.js';
import { generateRecommendations, generateRecommendationsStream } from './ai.js';
import {
  handleGetOriginal, handlePostTrainingData, handleGetTrainingData,
  handlePostConfig, handleGetConfig, handleClassify,
} from './quality.js';
import { handleAirflow } from './airflow.js';

const port = Number(process.env.PORT || 3000);
const jwtSecret = process.env.JWT_SECRET || 'change-me-secret';

// CORS_ORIGIN 은 쉼표 구분 다중 오리진 허용 (예: http://localhost:5173,http://localhost:8302)
// Access-Control-Allow-Origin 은 단일 값만 허용되므로 요청 오리진과 대조해 동적으로 반환한다.
const allowedOrigins = (process.env.CORS_ORIGIN || '*')
  .split(',').map(o => o.trim()).filter(Boolean);

function corsOrigin(req) {
  if (allowedOrigins.includes('*')) return '*';
  const origin = req.headers.origin || '';
  return allowedOrigins.includes(origin) ? origin : allowedOrigins[0];
}

// ── JWT helpers ────────────────────────────────────────────────────────────
function toBase64Url(input) {
  return Buffer.from(input).toString('base64')
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function signJwt(payload) {
  const header = toBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = `${header}.${toBase64Url(JSON.stringify(payload))}`;
  const sig = crypto.createHmac('sha256', jwtSecret).update(body)
    .digest('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${body}.${sig}`;
}

function verifyJwt(token) {
  const [header, payload, signature] = (token || '').split('.');
  if (!header || !payload || !signature) return null;
  const expected = crypto.createHmac('sha256', jwtSecret)
    .update(`${header}.${payload}`).digest('base64')
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  if (signature !== expected) return null;
  const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
  if (Date.now() / 1000 > data.exp) return null;
  return data;
}

// ── HTTP helpers ───────────────────────────────────────────────────────────
function sendJson(req, res, status, body) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': req ? corsOrigin(req) : (allowedOrigins[0] || '*'),
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
  });
  res.end(JSON.stringify(body));
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      if (!body) { resolve({}); return; }
      try { resolve(JSON.parse(body)); }
      catch { reject(new Error('invalid_json')); }
    });
  });
}

function requireAuth(req, res) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';
  const payload = verifyJwt(token);
  if (!payload) { sendJson(req, res, 401, { message: '인증이 필요합니다.' }); return null; }
  return payload;
}

function rows(result) {
  return (result ? result.split('\n') : []).filter(Boolean);
}

// ── Route table ────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') { sendJson(req, res, 204, {}); return; }

  const url = req.url?.split('?')[0] ?? '';
  const method = req.method ?? 'GET';

  // ── Health ────────────────────────────────────────────────────────────
  if (url === '/health' && method === 'GET') {
    try { await runQuery('SELECT 1;'); sendJson(req, res, 200, { status: 'ok' }); }
    catch { sendJson(req, res, 500, { status: 'db_error' }); }
    return;
  }

  // ── Auth: login ───────────────────────────────────────────────────────
  if (url === '/api/auth/login' && method === 'POST') {
    try {
      const { username, password } = await parseBody(req);
      if (!username || !password) {
        sendJson(req, res, 400, { message: 'username과 password는 필수입니다.' }); return;
      }
      const result = await runQuery(sql`
        SELECT id, username, display_name FROM users
        WHERE username = ${username}
          AND password_hash = crypt(${password}, password_hash)
        LIMIT 1;
      `);
      if (!result) {
        sendJson(req, res, 401, { message: '아이디 또는 비밀번호가 올바르지 않습니다.' }); return;
      }
      const [id, loginId, displayName] = result.split('\t');
      const token = signJwt({
        sub: Number(id), username: loginId, displayName,
        exp: Math.floor(Date.now() / 1000) + 60 * 60 * 8,
      });
      sendJson(req, res, 200, { token, user: { id: Number(id), username: loginId, displayName } });
    } catch { sendJson(req, res, 500, { message: '로그인 처리 중 오류가 발생했습니다.' }); }
    return;
  }

  // ── Portfolio: list ───────────────────────────────────────────────────
  if (url === '/api/investments' && method === 'GET') {
    const payload = requireAuth(req, res); if (!payload) return;
    try {
      const result = await runQuery(sql`
        SELECT id, ticker, asset_name, asset_type, quantity, avg_price, currency
        FROM investments WHERE user_id = ${payload.sub} ORDER BY created_at;
      `);
      const investments = rows(result).map((line) => {
        const [id, ticker, asset_name, asset_type, quantity, avg_price, currency] = line.split('\t');
        return { id: Number(id), ticker, asset_name, asset_type,
                 quantity: Number(quantity), avg_price: Number(avg_price), currency };
      });
      sendJson(req, res, 200, investments);
    } catch { sendJson(req, res, 500, { message: '포트폴리오 조회 실패' }); }
    return;
  }

  // ── Portfolio: add ────────────────────────────────────────────────────
  if (url === '/api/investments' && method === 'POST') {
    const payload = requireAuth(req, res); if (!payload) return;
    try {
      const { ticker, asset_name, asset_type = 'stock', quantity, avg_price, currency = 'KRW' }
        = await parseBody(req);
      if (!ticker || !asset_name || quantity == null || avg_price == null) {
        sendJson(req, res, 400, { message: 'ticker, asset_name, quantity, avg_price는 필수입니다.' }); return;
      }
      const result = await runQuery(sql`
        INSERT INTO investments (user_id, ticker, asset_name, asset_type, quantity, avg_price, currency)
        VALUES (${payload.sub}, ${ticker}, ${asset_name}, ${asset_type},
                ${quantity}, ${avg_price}, ${currency})
        RETURNING id;
      `);
      sendJson(req, res, 201, { id: Number(result.trim()) });
    } catch { sendJson(req, res, 500, { message: '포트폴리오 추가 실패' }); }
    return;
  }

  // ── Portfolio: delete ─────────────────────────────────────────────────
  const investmentDeleteMatch = url.match(/^\/api\/investments\/(\d+)$/);
  if (investmentDeleteMatch && method === 'DELETE') {
    const payload = requireAuth(req, res); if (!payload) return;
    const invId = investmentDeleteMatch[1];
    try {
      await runQuery(sql`
        DELETE FROM investments WHERE id = ${invId} AND user_id = ${payload.sub};
      `);
      sendJson(req, res, 200, { message: '삭제 완료' });
    } catch { sendJson(req, res, 500, { message: '삭제 실패' }); }
    return;
  }

  // ── Calendar events: list ─────────────────────────────────────────────
  if (url === '/api/calendar/events' && method === 'GET') {
    const payload = requireAuth(req, res); if (!payload) return;
    try {
      const result = await runQuery(sql`
        SELECT id, title, event_type, ticker, start_at::text, end_at::text,
               notes, is_ai_recommended::text, priority, status
        FROM investment_events
        WHERE user_id = ${payload.sub}
        ORDER BY start_at;
      `);
      const events = rows(result).map((line) => {
        const [id, title, event_type, ticker, start, end, notes, is_ai, priority, status]
          = line.split('\t');
        return { id: Number(id), title, event_type, ticker,
                 start: start, end: end,
                 notes, is_ai_recommended: is_ai === 't', priority, status };
      });
      sendJson(req, res, 200, events);
    } catch { sendJson(req, res, 500, { message: '캘린더 이벤트 조회 실패' }); }
    return;
  }

  // ── Calendar events: add ──────────────────────────────────────────────
  if (url === '/api/calendar/events' && method === 'POST') {
    const payload = requireAuth(req, res); if (!payload) return;
    try {
      const { title, event_type = 'general', ticker = null, start, end,
              notes = null, is_ai_recommended = false, priority = 'MEDIUM' }
        = await parseBody(req);
      if (!title || !start || !end) {
        sendJson(req, res, 400, { message: 'title, start, end는 필수입니다.' }); return;
      }
      const result = await runQuery(sql`
        INSERT INTO investment_events
          (user_id, title, event_type, ticker, start_at, end_at, notes, is_ai_recommended, priority)
        VALUES
          (${payload.sub}, ${title}, ${event_type}, ${ticker ?? ''},
           ${start}, ${end}, ${notes ?? ''},
           ${is_ai_recommended ? 'true' : 'false'}, ${priority})
        RETURNING id;
      `);
      sendJson(req, res, 201, { id: Number(result.trim()) });
    } catch { sendJson(req, res, 500, { message: '이벤트 추가 실패' }); }
    return;
  }

  // ── Calendar events: delete ───────────────────────────────────────────
  const eventDeleteMatch = url.match(/^\/api\/calendar\/events\/(\d+)$/);
  if (eventDeleteMatch && method === 'DELETE') {
    const payload = requireAuth(req, res); if (!payload) return;
    const evId = eventDeleteMatch[1];
    try {
      await runQuery(sql`
        DELETE FROM investment_events WHERE id = ${evId} AND user_id = ${payload.sub};
      `);
      sendJson(req, res, 200, { message: '삭제 완료' });
    } catch { sendJson(req, res, 500, { message: '삭제 실패' }); }
    return;
  }

  // ── AI recommendations (SSE streaming) ───────────────────────────────
  if (url === '/api/ai/recommend/stream' && method === 'POST') {
    const payload = requireAuth(req, res); if (!payload) return;

    res.writeHead(200, {
      'Content-Type':                'text/event-stream; charset=utf-8',
      'Cache-Control':               'no-cache',
      'Connection':                  'keep-alive',
      'Access-Control-Allow-Origin': corsOrigin(req),
      'Access-Control-Allow-Headers':'Content-Type, Authorization',
      'X-Accel-Buffering':           'no',
    });

    const send = (data) => { if (!res.writableEnded) res.write(`data: ${JSON.stringify(data)}\n\n`); };

    try {
      send({ type: 'progress', message: '포트폴리오 로딩 중...', percent: 3 });

      const result = await runQuery(sql`
        SELECT ticker, asset_name, asset_type, quantity, avg_price, currency
        FROM investments WHERE user_id = ${payload.sub} ORDER BY created_at;
      `);
      const portfolio = rows(result).map((line) => {
        const [ticker, asset_name, asset_type, quantity, avg_price, currency] = line.split('\t');
        return { ticker, asset_name, asset_type,
                 quantity: Number(quantity), avg_price: Number(avg_price), currency };
      });

      send({ type: 'progress', message: `포트폴리오 ${portfolio.length}개 종목 확인`, percent: 8 });

      const data = await generateRecommendationsStream(portfolio, send);

      send({ type: 'done', recommendations: data.recommendations });
    } catch (err) {
      send({ type: 'error', message: err.message });
    } finally {
      res.end();
    }
    return;
  }

  // ── AI recommendations (non-streaming, legacy) ────────────────────────
  if (url === '/api/ai/recommend' && method === 'POST') {
    const payload = requireAuth(req, res); if (!payload) return;
    try {
      const result = await runQuery(sql`
        SELECT ticker, asset_name, asset_type, quantity, avg_price, currency
        FROM investments WHERE user_id = ${payload.sub} ORDER BY created_at;
      `);
      const portfolio = rows(result).map((line) => {
        const [ticker, asset_name, asset_type, quantity, avg_price, currency] = line.split('\t');
        return { ticker, asset_name, asset_type,
                 quantity: Number(quantity), avg_price: Number(avg_price), currency };
      });
      const data = await generateRecommendations(portfolio);
      sendJson(req, res, 200, data);
    } catch (err) {
      sendJson(req, res, 500, { message: 'AI 추천 생성 실패: ' + err.message });
    }
    return;
  }

  // ── Airflow 프록시 (인증 필요) ───────────────────────────────────────────
  if (url.startsWith('/api/airflow')) {
    const payload = requireAuth(req, res); if (!payload) return;
    return handleAirflow(req, res, sendJson);
  }

  // ── Quality Inspection ────────────────────────────────────────────────
  if (url === '/api/quality/original' && method === 'GET')
    return handleGetOriginal(req, res, sendJson);

  if (url === '/api/quality/training-data' && method === 'POST')
    return handlePostTrainingData(req, res, sendJson, parseBody);

  if (url === '/api/quality/training-data' && method === 'GET')
    return handleGetTrainingData(req, res, sendJson);

  if (url === '/api/quality/config' && method === 'POST')
    return handlePostConfig(req, res, sendJson, parseBody);

  if (url === '/api/quality/config' && method === 'GET')
    return handleGetConfig(req, res, sendJson);

  if (url === '/api/quality/classify' && method === 'POST') {
    const payload = requireAuth(req, res); if (!payload) return;
    return handleClassify(req, res, sendJson, parseBody);
  }

  sendJson(req, res, 404, { message: 'Not found' });
});

server.listen(port, () => {
  console.log(`Investment Advisor API listening on port ${port}`);
});
