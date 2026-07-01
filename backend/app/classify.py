#!/usr/bin/env python3
"""
classify.py — 정품/불량품 이미지 분류기
사용법: python3 classify.py <test_image_path>
출력:  JSON { result, label, confidence, reason, ssim_score, method }
"""
import sys
import os
import json
import base64
import math
import requests
from PIL import Image, ImageFilter
import numpy as np

ORIGINAL_PATH  = os.environ.get('ORIGINAL_IMAGE',  '/home/ubuntu/invest-flow/DATA-ROOT/50597846-precision-mechanics.avif')
OLLAMA_URL     = os.environ.get('OLLAMA_URL',       'http://172.29.32.1:11300')
VISION_MODEL   = os.environ.get('OLLAMA_VISION_MODEL', 'llava:34b')
THRESHOLD_FILE = os.environ.get('THRESHOLD_FILE',   '/home/ubuntu/invest-flow/DATA-ROOT/model/thresholds.json')

# ── 이미지 유사도 계산 (PIL + numpy) ─────────────────────────────────────────

def _resize_gray(path, size=(256, 256)):
    return np.array(Image.open(path).convert('RGB').resize(size), dtype=np.float32)

def pixel_similarity(path1, path2, size=(256, 256)):
    """픽셀 MSE 기반 유사도 (0~1, 높을수록 유사)"""
    a = _resize_gray(path1, size)
    b = _resize_gray(path2, size)
    mse = float(np.mean((a - b) ** 2))
    return 1.0 / (1.0 + mse / 500.0)

def histogram_similarity(path1, path2, bins=64):
    """RGB 히스토그램 교차 유사도 (0~1, 채널별 평균)"""
    def per_channel_hists(path):
        img = Image.open(path).convert('RGB').resize((256, 256))
        hists = []
        for ch in img.split():
            arr = np.array(ch).flatten()
            counts, _ = np.histogram(arr, bins=bins, range=(0, 255))
            total = counts.sum() or 1
            hists.append(counts / total)
        return hists
    h1s, h2s = per_channel_hists(path1), per_channel_hists(path2)
    channel_sims = [float(np.sum(np.minimum(h1, h2))) for h1, h2 in zip(h1s, h2s)]
    return sum(channel_sims) / len(channel_sims)

def combined_similarity(path1, path2):
    """픽셀(50%) + 히스토그램(50%) 결합 유사도"""
    ps = pixel_similarity(path1, path2)
    hs = histogram_similarity(path1, path2)
    return 0.5 * ps + 0.5 * hs

# ── Ollama 비전 분류 ──────────────────────────────────────────────────────────

def classify_with_ollama(test_path):
    """llava 비전 모델로 정품/불량품 판단. 실패 시 None 반환."""
    try:
        with open(ORIGINAL_PATH, 'rb') as f:
            orig_b64 = base64.b64encode(f.read()).decode()
        with open(test_path, 'rb') as f:
            test_b64 = base64.b64encode(f.read()).decode()

        prompt = (
            '다음 두 이미지를 비교하세요. '
            '첫 번째 이미지는 정품 원본 정밀 기계 부품입니다. '
            '두 번째 이미지가 정품(y)인지 불량품(n)인지 판단하세요. '
            '정품 기준: 원본과 동일한 형태·색상·구조를 유지. '
            '불량품 기준: 손상, 변형, 이물질, 색상 이상, 형태 변형 등. '
            '반드시 순수 JSON만 응답하세요 (다른 텍스트 없이):\n'
            '{"result":"y","confidence":0.9,"reason":"이유 한국어"}'
        )

        resp = requests.post(
            f'{OLLAMA_URL}/api/chat',
            json={
                'model':   VISION_MODEL,
                'stream':  False,
                'think':   False,
                'options': {'temperature': 0.1},
                'messages': [{
                    'role':    'user',
                    'content': prompt,
                    'images':  [orig_b64, test_b64],
                }],
            },
            timeout=180,
        )
        content = resp.json()['message']['content'].strip()

        # JSON 추출 (마크다운 코드블록 처리)
        import re
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        content = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', content).strip()
        m = re.search(r'\{[\s\S]*\}', content)
        if not m:
            return None
        parsed = json.loads(m.group())
        if parsed.get('result') not in ('y', 'n'):
            return None
        return parsed
    except Exception as e:
        print(f'[warn] Ollama 분류 실패: {e}', file=sys.stderr)
        return None

# ── 임계값 로드 ───────────────────────────────────────────────────────────────

def load_threshold():
    if os.path.exists(THRESHOLD_FILE):
        with open(THRESHOLD_FILE) as f:
            return json.load(f).get('similarity_threshold', 0.72)
    return 0.72  # 기본값: Airflow DAG 실행 전 보수적 기본값

# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'test_image_path 인수 필요'}))
        sys.exit(1)

    test_path = sys.argv[1]
    if not os.path.exists(test_path):
        print(json.dumps({'error': f'파일을 찾을 수 없습니다: {test_path}'}))
        sys.exit(1)

    sim = combined_similarity(ORIGINAL_PATH, test_path)
    threshold = load_threshold()

    # Ollama 비전 모델 우선 시도
    ollama = classify_with_ollama(test_path)

    if ollama:
        result     = ollama['result']
        confidence = float(ollama.get('confidence', 0.85))
        reason     = ollama.get('reason', 'AI 비전 분석 결과')
        method     = 'ollama_vision'
    else:
        result     = 'y' if sim >= threshold else 'n'
        confidence = min(0.95, max(0.5, abs(sim - threshold) / threshold + 0.6))
        reason     = f'이미지 유사도 {sim:.1%} (임계값 {threshold:.1%})'
        method     = 'similarity'

    print(json.dumps({
        'result':     result,
        'label':      '정품' if result == 'y' else '불량품',
        'confidence': round(confidence, 3),
        'reason':     reason,
        'sim_score':  round(sim, 4),
        'method':     method,
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
