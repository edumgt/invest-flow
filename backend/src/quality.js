/**
 * quality.js — 정품/불량품 검사 모듈
 * 엔드포인트:
 *   GET  /api/quality/original          원본 이미지 반환 (base64)
 *   POST /api/quality/training-data     Airflow DAG가 생성한 학습 이미지 저장
 *   GET  /api/quality/training-data     학습·검증 이미지 목록
 *   POST /api/quality/config            임계값 설정 저장 (Airflow 완료 시 호출)
 *   GET  /api/quality/config            현재 설정 반환
 *   POST /api/quality/classify          이미지 분류 (classify.py 호출)
 */
import { createReadStream, existsSync, mkdirSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';

const execFileAsync = promisify(execFile);

const DATA_ROOT     = process.env.DATA_ROOT     || '/home/ubuntu/invest-flow/DATA-ROOT';
const ORIGINAL_PATH = path.join(DATA_ROOT, '50597846-precision-mechanics.avif');
const TRAIN_DIR     = path.join(DATA_ROOT, 'train');
const VAL_DIR       = path.join(DATA_ROOT, 'val');
const MODEL_DIR     = path.join(DATA_ROOT, 'model');
const CONFIG_PATH   = path.join(MODEL_DIR, 'thresholds.json');
const CLASSIFY_PY   = path.join(import.meta.dirname, 'classify.py');

for (const d of [TRAIN_DIR, VAL_DIR, MODEL_DIR]) {
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

// ── 원본 이미지 반환 ──────────────────────────────────────────────────────────
export async function handleGetOriginal(req, res, sendJson) {
  if (!existsSync(ORIGINAL_PATH)) {
    return sendJson(req, res, 404, { message: '원본 이미지를 찾을 수 없습니다.' });
  }
  const data = readFileSync(ORIGINAL_PATH);
  const b64  = data.toString('base64');
  sendJson(req, res, 200, { base64: b64, mimeType: 'image/avif' });
}

// ── 학습 이미지 저장 (Airflow DAG → Backend) ──────────────────────────────────
export async function handlePostTrainingData(req, res, sendJson, parseBody) {
  try {
    const body = await parseBody(req);
    // body: { filename, base64, split: 'train'|'val', label: 'y'|'n' }
    const { filename, base64: b64, split = 'train', label } = body;
    if (!filename || !b64 || !label) {
      return sendJson(req, res, 400, { message: 'filename, base64, label 필수' });
    }
    if (!['y', 'n'].includes(label)) {
      return sendJson(req, res, 400, { message: 'label 은 y 또는 n' });
    }

    const dir     = split === 'val' ? VAL_DIR : TRAIN_DIR;
    const outPath = path.join(dir, filename);
    writeFileSync(outPath, Buffer.from(b64, 'base64'));
    sendJson(req, res, 201, { saved: outPath });
  } catch (err) {
    sendJson(req, res, 500, { message: err.message });
  }
}

// ── 학습 이미지 목록 반환 ─────────────────────────────────────────────────────
export async function handleGetTrainingData(req, res, sendJson) {
  const list = (dir, split) =>
    (existsSync(dir) ? readdirSync(dir) : [])
      .filter(f => /\.(jpg|jpeg|png|webp)$/i.test(f))
      .sort()
      .map(f => {
        const label = f.startsWith('y_') ? 'y' : f.startsWith('n_') ? 'n' : '?';
        const data  = readFileSync(path.join(dir, f));
        return { filename: f, split, label, base64: data.toString('base64') };
      });

  sendJson(req, res, 200, {
    train: list(TRAIN_DIR, 'train'),
    val:   list(VAL_DIR,   'val'),
  });
}

// ── 설정 저장 (Airflow 완료 시) ───────────────────────────────────────────────
export async function handlePostConfig(req, res, sendJson, parseBody) {
  try {
    const body = await parseBody(req);
    writeFileSync(CONFIG_PATH, JSON.stringify(body, null, 2));
    sendJson(req, res, 200, { saved: CONFIG_PATH });
  } catch (err) {
    sendJson(req, res, 500, { message: err.message });
  }
}

// ── 현재 설정 반환 ────────────────────────────────────────────────────────────
export async function handleGetConfig(req, res, sendJson) {
  if (!existsSync(CONFIG_PATH)) {
    return sendJson(req, res, 200, {
      similarity_threshold: 0.72,
      trained: false,
      train_accuracy: null,
      val_accuracy: null,
    });
  }
  sendJson(req, res, 200, JSON.parse(readFileSync(CONFIG_PATH, 'utf8')));
}

// ── 이미지 분류 ───────────────────────────────────────────────────────────────
export async function handleClassify(req, res, sendJson, parseBody) {
  let tmpPath = null;
  try {
    const body = await parseBody(req);
    const { base64: b64, mimeType = 'image/jpeg' } = body;
    if (!b64) return sendJson(req, res, 400, { message: 'base64 이미지 데이터 필요' });

    // 임시 파일에 저장
    const ext  = mimeType.includes('png') ? '.png'
               : mimeType.includes('webp') ? '.webp'
               : '.jpg';
    tmpPath = path.join(os.tmpdir(), `qc_${randomUUID()}${ext}`);
    writeFileSync(tmpPath, Buffer.from(b64, 'base64'));

    // Python 분류기 호출 (최대 3분)
    const env = {
      ...process.env,
      ORIGINAL_IMAGE:       ORIGINAL_PATH,
      THRESHOLD_FILE:       CONFIG_PATH,
      OLLAMA_URL:           process.env.OLLAMA_URL   || 'http://172.29.32.1:11300',
      OLLAMA_VISION_MODEL:  process.env.OLLAMA_VISION_MODEL || 'llava:34b',
    };
    const { stdout, stderr } = await execFileAsync(
      'python3', [CLASSIFY_PY, tmpPath],
      { env, timeout: 180_000 }
    );
    if (stderr) console.warn('[classify]', stderr.trim());

    const result = JSON.parse(stdout.trim());
    sendJson(req, res, 200, result);
  } catch (err) {
    sendJson(req, res, 500, { message: `분류 오류: ${err.message}` });
  } finally {
    if (tmpPath && existsSync(tmpPath)) {
      import('node:fs').then(fs => fs.unlinkSync(tmpPath)).catch(() => {});
    }
  }
}
