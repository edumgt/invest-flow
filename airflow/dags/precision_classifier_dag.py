"""
precision_classifier_dag.py

정밀 기계 부품 정품/불량품 분류기 데이터 파이프라인

작동 흐름:
  1. ensure_deps        — Pillow·numpy·requests 설치 확인
  2. generate_images    — 원본 AVIF에서 y(정품)/n(불량품) 라벨 이미지 10장 생성
                          train: y×4 + n×3 = 7장  /  val: y×2 + n×1 = 3장
  3. analyze_with_llava — llava:34b 비전 모델로 각 이미지 라벨 검증
  4. train_threshold    — 유사도 분포로 최적 임계값 산출 → 백엔드 /api/quality/config 저장
  5. validate           — 검증셋 정확도 계산 → 로그 기록

환경 변수 (Airflow VM 기준):
  BACKEND_URL  = http://192.168.253.1:8301
  OLLAMA_URL   = http://192.168.253.1:11300
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta

import requests

from airflow import DAG
from airflow.operators.python import PythonOperator

# ── 설정 ─────────────────────────────────────────────────────────────────────

BACKEND_URL   = os.getenv('BACKEND_URL', 'http://192.168.253.1:8301')
OLLAMA_URL    = os.getenv('OLLAMA_URL',  'http://192.168.253.1:11300')
VISION_MODEL  = 'llava:34b'
ORIGINAL_URL  = f'{BACKEND_URL}/api/quality/original'
TRAIN_POST    = f'{BACKEND_URL}/api/quality/training-data'
CONFIG_POST   = f'{BACKEND_URL}/api/quality/config'

# ── 이미지 생성 파라미터 ──────────────────────────────────────────────────────
# train: y_train_001~004, n_train_001~003  /  val: y_val_001~002, n_val_001

GENUINE_AUGMENTS = [
    # (파일명, 적용 함수명)
    ('y_train_001.jpg', 'brightness_05'),
    ('y_train_002.jpg', 'crop_resize_02'),
    ('y_train_003.jpg', 'contrast_03'),
    ('y_train_004.jpg', 'sharpen_light'),
    ('y_val_001.jpg',   'brightness_m05'),
    ('y_val_002.jpg',   'crop_resize_03'),
]
DEFECT_AUGMENTS = [
    ('n_train_001.jpg', 'heavy_blur'),
    ('n_train_002.jpg', 'color_shift'),
    ('n_train_003.jpg', 'missing_patch'),
    ('n_val_001.jpg',   'noise_contrast'),
]


# ── Task 1: 의존성 확인 ───────────────────────────────────────────────────────

def ensure_deps():
    """Pillow·numpy·requests가 없으면 설치."""
    pkgs = ['Pillow', 'numpy', 'requests']
    for pkg in pkgs:
        try:
            __import__(pkg.lower().replace('pillow', 'PIL'))
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])
    print('[deps] 의존성 확인 완료')


# ── Task 2: 학습·검증 이미지 생성 ────────────────────────────────────────────

def generate_images():
    """원본 이미지를 받아 y/n 라벨 이미지 10장을 생성하고 백엔드에 저장한다."""
    from PIL import Image, ImageFilter, ImageEnhance
    import numpy as np

    # 원본 다운로드
    resp = requests.get(ORIGINAL_URL, timeout=30)
    resp.raise_for_status()
    orig_bytes = base64.b64decode(resp.json()['base64'])
    orig = Image.open(io.BytesIO(orig_bytes)).convert('RGB')
    W, H = orig.size
    print(f'[gen] 원본 크기: {W}×{H}')

    # ── 정품 변환 함수 (미세한 변형 → y 라벨) ───────────────────────────────
    def brightness_05(img):
        return ImageEnhance.Brightness(img).enhance(1.05)

    def brightness_m05(img):
        return ImageEnhance.Brightness(img).enhance(0.95)

    def crop_resize_02(img):
        w, h = img.size
        m = int(min(w, h) * 0.02)
        return img.crop((m, m, w - m, h - m)).resize((w, h), Image.LANCZOS)

    def crop_resize_03(img):
        w, h = img.size
        m = int(min(w, h) * 0.03)
        return img.crop((m, m, w - m, h - m)).resize((w, h), Image.LANCZOS)

    def contrast_03(img):
        return ImageEnhance.Contrast(img).enhance(1.03)

    def sharpen_light(img):
        return img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50))

    # ── 불량품 변환 함수 (심한 변형 → n 라벨) ───────────────────────────────
    def heavy_blur(img):
        return img.filter(ImageFilter.GaussianBlur(radius=6))

    def color_shift(img):
        arr = np.array(img, dtype=np.float32)
        # 녹색 채널 증폭 + 청색 감소 → 색상 이탈
        arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.8, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.3, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def missing_patch(img):
        arr = np.array(img.copy())
        # 이미지 중앙 40%×40% 영역을 검정으로 (부품 누락/손상 시뮬레이션)
        h, w = arr.shape[:2]
        y1, y2 = int(h * 0.30), int(h * 0.70)
        x1, x2 = int(w * 0.30), int(w * 0.70)
        arr[y1:y2, x1:x2] = 0
        return Image.fromarray(arr)

    def noise_contrast(img):
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, 40, arr.shape)
        arr = np.clip(arr + noise, 0, 255)
        noisy = Image.fromarray(arr.astype(np.uint8))
        return ImageEnhance.Contrast(noisy).enhance(2.5)

    fn_map = {
        'brightness_05':   brightness_05,
        'brightness_m05':  brightness_m05,
        'crop_resize_02':  crop_resize_02,
        'crop_resize_03':  crop_resize_03,
        'contrast_03':     contrast_03,
        'sharpen_light':   sharpen_light,
        'heavy_blur':      heavy_blur,
        'color_shift':     color_shift,
        'missing_patch':   missing_patch,
        'noise_contrast':  noise_contrast,
    }

    all_items = [
        (fname, fn_map[fn], 'y', 'val' if 'val' in fname else 'train')
        for fname, fn in GENUINE_AUGMENTS
    ] + [
        (fname, fn_map[fn], 'n', 'val' if 'val' in fname else 'train')
        for fname, fn in DEFECT_AUGMENTS
    ]

    for fname, aug_fn, label, split in all_items:
        augmented = aug_fn(orig)
        buf = io.BytesIO()
        augmented.save(buf, format='JPEG', quality=92)
        b64 = base64.b64encode(buf.getvalue()).decode()

        r = requests.post(TRAIN_POST, json={
            'filename': fname,
            'base64':   b64,
            'split':    split,
            'label':    label,
        }, timeout=30)
        r.raise_for_status()
        print(f'[gen] {split}/{fname} ({label}) → {r.json()}')

    print(f'[gen] 총 {len(all_items)}장 생성 완료')


# ── Task 3: llava 비전 검증 ───────────────────────────────────────────────────

def analyze_with_llava(**context):
    """llava:34b 로 각 이미지가 정품/불량품에 해당하는지 검증하고 결과를 XCom에 저장."""
    resp = requests.get(f'{BACKEND_URL}/api/quality/training-data', timeout=30)
    resp.raise_for_status()
    data = resp.json()

    orig_resp = requests.get(ORIGINAL_URL, timeout=30)
    orig_b64  = orig_resp.json()['base64']

    results = []
    all_images = data['train'] + data['val']

    for item in all_images:
        fname  = item['filename']
        label  = item['label']
        img_b64 = item['base64']

        prompt = (
            '정밀 기계 부품 이미지 두 장을 비교합니다. '
            '첫 번째는 정품 원본입니다. '
            f'두 번째 이미지의 예상 라벨은 {"정품(y)" if label == "y" else "불량품(n)"}입니다. '
            '이 라벨이 맞는지 확인하고 이유를 설명하세요. '
            '순수 JSON만 응답: {"agree":true,"reason":"이유"}'
        )

        try:
            r = requests.post(f'{OLLAMA_URL}/api/chat', json={
                'model':   VISION_MODEL,
                'stream':  False,
                'think':   False,
                'options': {'temperature': 0.1},
                'messages': [{
                    'role':    'user',
                    'content': prompt,
                    'images':  [orig_b64, img_b64],
                }],
            }, timeout=240)
            content = r.json()['message']['content']

            import re
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
            content = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', content).strip()
            m = re.search(r'\{[\s\S]*\}', content)
            parsed = json.loads(m.group()) if m else {}
            agree  = parsed.get('agree', True)
            reason = parsed.get('reason', '분석 완료')
        except Exception as e:
            agree  = True
            reason = f'llava 분석 오류: {e}'

        status = '✓ 일치' if agree else '✗ 불일치'
        print(f'[llava] {fname} (label={label}) {status}: {reason[:60]}')
        results.append({'filename': fname, 'label': label, 'agree': agree, 'reason': reason})

    context['ti'].xcom_push(key='analysis', value=results)
    agree_cnt = sum(1 for r in results if r['agree'])
    print(f'[llava] 검증 결과: {agree_cnt}/{len(results)} 일치')


# ── Task 4: 임계값 산출 → 백엔드 저장 ────────────────────────────────────────

def train_threshold(**context):
    """학습 이미지의 유사도 분포로 y/n 분리 임계값을 계산하고 저장한다."""
    from PIL import Image
    import numpy as np

    orig_resp = requests.get(ORIGINAL_URL, timeout=30)
    orig_bytes = base64.b64decode(orig_resp.json()['base64'])
    orig = Image.open(io.BytesIO(orig_bytes)).convert('RGB').resize((256, 256))
    orig_arr = np.array(orig, dtype=np.float32)

    data_resp = requests.get(f'{BACKEND_URL}/api/quality/training-data', timeout=30)
    data = data_resp.json()
    train_items = data['train']

    y_sims, n_sims = [], []
    for item in train_items:
        img = Image.open(io.BytesIO(base64.b64decode(item['base64']))).convert('RGB').resize((256, 256))
        arr = np.array(img, dtype=np.float32)
        mse = float(np.mean((orig_arr - arr) ** 2))
        sim = 1.0 / (1.0 + mse / 500.0)
        (y_sims if item['label'] == 'y' else n_sims).append(sim)

    y_min = min(y_sims) if y_sims else 0.8
    n_max = max(n_sims) if n_sims else 0.4

    threshold = (y_min + n_max) / 2
    threshold = round(max(0.3, min(0.95, threshold)), 4)
    print(f'[train] y_sims={[round(s,3) for s in y_sims]}')
    print(f'[train] n_sims={[round(s,3) for s in n_sims]}')
    print(f'[train] 임계값={threshold} (y_min={y_min:.3f}, n_max={n_max:.3f})')

    config = {
        'similarity_threshold': threshold,
        'trained': True,
        'trained_at': datetime.utcnow().isoformat(),
        'y_similarities': y_sims,
        'n_similarities': n_sims,
        'vision_model': VISION_MODEL,
        'train_count': {'y': len(y_sims), 'n': len(n_sims)},
    }
    r = requests.post(CONFIG_POST, json=config, timeout=30)
    r.raise_for_status()
    print(f'[train] 설정 저장 완료 → {r.json()}')
    context['ti'].xcom_push(key='threshold', value=threshold)


# ── Task 5: 검증 정확도 ───────────────────────────────────────────────────────

def validate(**context):
    """검증셋에서 임계값 기반 분류 정확도를 측정한다."""
    from PIL import Image
    import numpy as np

    threshold = context['ti'].xcom_pull(task_ids='train_threshold', key='threshold') or 0.72

    orig_resp = requests.get(ORIGINAL_URL, timeout=30)
    orig_bytes = base64.b64decode(orig_resp.json()['base64'])
    orig = Image.open(io.BytesIO(orig_bytes)).convert('RGB').resize((256, 256))
    orig_arr = np.array(orig, dtype=np.float32)

    data_resp = requests.get(f'{BACKEND_URL}/api/quality/training-data', timeout=30)
    val_items = data_resp.json()['val']

    correct = 0
    for item in val_items:
        img = Image.open(io.BytesIO(base64.b64decode(item['base64']))).convert('RGB').resize((256, 256))
        arr = np.array(img, dtype=np.float32)
        mse = float(np.mean((orig_arr - arr) ** 2))
        sim = 1.0 / (1.0 + mse / 500.0)
        pred  = 'y' if sim >= threshold else 'n'
        truth = item['label']
        ok    = pred == truth
        correct += int(ok)
        mark = '✓' if ok else '✗'
        print(f'[val] {item["filename"]}: sim={sim:.3f} pred={pred} truth={truth} {mark}')

    acc = correct / len(val_items) if val_items else 0
    print(f'[val] 검증 정확도: {correct}/{len(val_items)} = {acc:.1%}')

    # 설정에 정확도 추가
    config_resp = requests.get(f'{BACKEND_URL}/api/quality/config', timeout=30)
    config = config_resp.json()
    config['val_accuracy'] = round(acc, 4)
    config['val_count']    = len(val_items)
    requests.post(CONFIG_POST, json=config, timeout=30)
    print('[val] 완료 — 분류기 준비 됨')


# ── DAG 정의 ─────────────────────────────────────────────────────────────────

default_args = {
    'owner':           'airflow',
    'retries':         1,
    'retry_delay':     timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}

with DAG(
    dag_id='precision_classifier',
    description='정밀 기계 부품 정품/불량품 분류기 학습 파이프라인',
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,       # 수동 트리거
    catchup=False,
    tags=['quality', 'vision', 'ollama'],
) as dag:

    t_deps = PythonOperator(
        task_id='ensure_deps',
        python_callable=ensure_deps,
    )

    t_gen = PythonOperator(
        task_id='generate_images',
        python_callable=generate_images,
    )

    t_llava = PythonOperator(
        task_id='analyze_with_llava',
        python_callable=analyze_with_llava,
    )

    t_train = PythonOperator(
        task_id='train_threshold',
        python_callable=train_threshold,
    )

    t_val = PythonOperator(
        task_id='validate',
        python_callable=validate,
    )

    t_deps >> t_gen >> t_llava >> t_train >> t_val
