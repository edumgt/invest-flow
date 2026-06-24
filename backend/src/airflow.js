/**
 * airflow.js — Airflow REST API 프록시
 *
 * 브라우저 → 백엔드 /api/airflow/* → Airflow 8793/api/v1/*
 *
 * 지원 엔드포인트:
 *   GET  /api/airflow/dags                              DAG 목록
 *   GET  /api/airflow/dags/:dagId                       DAG 상세
 *   GET  /api/airflow/dags/:dagId/runs                  런 히스토리
 *   GET  /api/airflow/dags/:dagId/runs/:runId/tasks     태스크 인스턴스
 *   POST /api/airflow/dags/:dagId/trigger               DAG 수동 실행
 *   POST /api/airflow/dags/:dagId/pause                 DAG 일시정지
 *   POST /api/airflow/dags/:dagId/unpause               DAG 재개
 */

const AIRFLOW_URL  = process.env.AIRFLOW_URL  || 'http://192.168.253.149:8793';
const AIRFLOW_USER = process.env.AIRFLOW_USER || 'admin';
const AIRFLOW_PASS = process.env.AIRFLOW_PASS || 'admin';

const AUTH_HEADER = 'Basic ' + Buffer.from(`${AIRFLOW_USER}:${AIRFLOW_PASS}`).toString('base64');

// ── Airflow REST API 공통 호출 ────────────────────────────────────────────────

async function afFetch(path, options = {}) {
  const url = `${AIRFLOW_URL}/api/v1${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: AUTH_HEADER,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  const body = await res.json().catch(() => ({ error: 'JSON parse failed' }));
  return { status: res.status, body };
}

// ── 라우트 핸들러 ─────────────────────────────────────────────────────────────

export async function handleAirflow(req, res, sendJson) {
  // /api/airflow 이하 경로 파싱
  const suffix = (req.url?.split('?')[0] ?? '').replace(/^\/api\/airflow/, '');
  const method = req.method ?? 'GET';
  const qs     = req.url?.includes('?') ? '?' + req.url.split('?')[1] : '';

  // GET /api/airflow/dags
  if (suffix === '/dags' && method === 'GET') {
    const { status, body } = await afFetch(`/dags?limit=100${qs ? '&' + qs.slice(1) : ''}`);
    return sendJson(req, res, status, body);
  }

  // GET /api/airflow/dags/:dagId
  const dagMatch = suffix.match(/^\/dags\/([^/]+)$/);
  if (dagMatch && method === 'GET') {
    const { status, body } = await afFetch(`/dags/${encodeURIComponent(dagMatch[1])}`);
    return sendJson(req, res, status, body);
  }

  // GET /api/airflow/dags/:dagId/runs
  const runsMatch = suffix.match(/^\/dags\/([^/]+)\/runs$/);
  if (runsMatch && method === 'GET') {
    const dagId = encodeURIComponent(runsMatch[1]);
    const limit = new URLSearchParams(qs.slice(1)).get('limit') || '10';
    const { status, body } = await afFetch(
      `/dags/${dagId}/dagRuns?limit=${limit}&order_by=-start_date`
    );
    return sendJson(req, res, status, body);
  }

  // GET /api/airflow/dags/:dagId/runs/:runId/tasks
  const tasksMatch = suffix.match(/^\/dags\/([^/]+)\/runs\/([^/]+)\/tasks$/);
  if (tasksMatch && method === 'GET') {
    const dagId = encodeURIComponent(decodeURIComponent(tasksMatch[1]));
    // run_id 는 프론트에서 이미 인코딩해서 보내므로 디코딩 후 재인코딩으로 이중 인코딩 방지
    const runId = encodeURIComponent(decodeURIComponent(tasksMatch[2]));
    const { status, body } = await afFetch(
      `/dags/${dagId}/dagRuns/${runId}/taskInstances`
    );
    return sendJson(req, res, status, body);
  }

  // POST /api/airflow/dags/:dagId/trigger
  const triggerMatch = suffix.match(/^\/dags\/([^/]+)\/trigger$/);
  if (triggerMatch && method === 'POST') {
    const dagId = encodeURIComponent(triggerMatch[1]);
    const now   = new Date().toISOString();
    const { status, body } = await afFetch(
      `/dags/${dagId}/dagRuns`,
      {
        method: 'POST',
        body:   JSON.stringify({ dag_run_id: `manual__${now}`, conf: {} }),
      }
    );
    return sendJson(req, res, status, body);
  }

  // POST /api/airflow/dags/:dagId/pause  or  /unpause
  const pauseMatch = suffix.match(/^\/dags\/([^/]+)\/(pause|unpause)$/);
  if (pauseMatch && method === 'POST') {
    const dagId   = encodeURIComponent(pauseMatch[1]);
    const isPaused = pauseMatch[2] === 'pause';
    const { status, body } = await afFetch(
      `/dags/${dagId}`,
      {
        method: 'PATCH',
        body:   JSON.stringify({ is_paused: isPaused }),
      }
    );
    return sendJson(req, res, status, body);
  }

  sendJson(req, res, 404, { message: `Airflow 라우트 없음: ${method} ${suffix}` });
}
