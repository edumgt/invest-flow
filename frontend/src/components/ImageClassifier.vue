<template>
  <div class="space-y-5">

    <!-- 상단: 원본 + 현재 설정 -->
    <div class="grid gap-4 md:grid-cols-2">

      <!-- 원본 기준 이미지 -->
      <div class="card-bk overflow-hidden">
        <div class="border-b border-bk-border px-5 py-3 flex items-center gap-2">
          <i class="fa-solid fa-shield-check text-bk-yellow text-sm"></i>
          <span class="text-sm font-semibold text-bk-text">정품 원본 기준 이미지</span>
          <span class="ml-auto rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-400">REF</span>
        </div>
        <div class="p-4 flex items-center justify-center bg-bk-bg min-h-[200px]">
          <img v-if="originalSrc" :src="originalSrc" alt="원본"
               class="max-h-52 rounded-lg object-contain shadow" />
          <div v-else class="flex flex-col items-center gap-2 text-bk-text-3 text-sm">
            <i class="fa-solid fa-spinner fa-spin text-xl"></i>
            <span>원본 로딩 중...</span>
          </div>
        </div>
        <div class="px-5 pb-4 text-xs text-bk-text-3">
          50597846-precision-mechanics — 비교 기준 이미지
        </div>
      </div>

      <!-- 학습 상태 카드 -->
      <div class="card-bk overflow-hidden">
        <div class="border-b border-bk-border px-5 py-3 flex items-center gap-2">
          <i class="fa-solid fa-microchip text-bk-yellow text-sm"></i>
          <span class="text-sm font-semibold text-bk-text">분류기 상태</span>
          <span class="ml-auto rounded-full px-2 py-0.5 text-xs"
                :class="config.trained ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'">
            {{ config.trained ? '학습 완료' : 'Airflow DAG 실행 필요' }}
          </span>
        </div>
        <div class="p-4 space-y-3">
          <div class="grid grid-cols-2 gap-2">
            <StatCard label="모델" :value="config.vision_model || 'llava:34b'" />
            <StatCard label="유사도 임계값"
                  :value="config.similarity_threshold != null
                    ? (Number(config.similarity_threshold) * 100).toFixed(1) + '%' : '—'" />
            <StatCard label="학습 이미지"
                  :value="config.train_count
                    ? `y:${(config.train_count as any).y} / n:${(config.train_count as any).n}` : '—'" />
            <StatCard label="검증 정확도"
                  :value="config.val_accuracy != null
                    ? (Number(config.val_accuracy) * 100).toFixed(0) + '%' : '—'" />
          </div>
          <div v-if="!config.trained" class="rounded-lg bg-yellow-500/5 border border-yellow-500/20 px-4 py-3 text-xs text-yellow-400">
            <i class="fa-solid fa-circle-info mr-1.5"></i>
            Airflow UI에서 <strong>precision_classifier</strong> DAG를 실행하면<br>
            자동으로 학습 이미지 10장 생성 + 임계값 계산이 진행됩니다.
          </div>
        </div>
      </div>
    </div>

    <!-- 학습/검증 이미지 갤러리 -->
    <div v-if="trainImages.length || valImages.length" class="card-bk overflow-hidden">
      <div class="border-b border-bk-border px-5 py-3 flex items-center gap-2">
        <i class="fa-solid fa-images text-bk-yellow text-sm"></i>
        <span class="text-sm font-semibold text-bk-text">학습·검증 데이터셋</span>
        <span class="ml-2 text-xs text-bk-text-3">총 {{ trainImages.length + valImages.length }}장</span>
        <button class="ml-auto text-xs text-bk-text-3 hover:text-bk-yellow transition-colors"
                @click="loadTrainingData">
          <i class="fa-solid fa-rotate-right mr-1"></i>새로고침
        </button>
      </div>
      <div class="p-4 space-y-3">
        <GalleryRow v-if="trainImages.length" label="학습셋 (train)" :items="trainImages" />
        <GalleryRow v-if="valImages.length"   label="검증셋 (val)"   :items="valImages"   />
      </div>
    </div>

    <!-- 이미지 분류 영역 -->
    <div class="card-bk overflow-hidden">
      <div class="border-b border-bk-border bg-[#0a0e1a] px-5 py-3 flex items-center gap-2">
        <i class="fa-solid fa-magnifying-glass text-bk-yellow text-sm"></i>
        <span class="text-sm font-semibold text-bk-text">정품 검사</span>
        <span class="ml-auto text-xs text-bk-text-3">이미지를 업로드해 원본과 비교합니다</span>
      </div>

      <!-- 진행바 -->
      <div v-if="classifying" class="bg-[#0a0e1a] px-5 pb-3">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-xs text-bk-text-3">{{ progressMsg }}</span>
          <span class="text-xs text-bk-yellow">{{ progressPct }}%</span>
        </div>
        <div class="h-1.5 rounded-full bg-bk-elevated overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500"
               style="background: linear-gradient(90deg,#F7B731 0%,#0F6CBD 100%)"
               :style="{ width: progressPct + '%' }" />
        </div>
      </div>

      <div class="p-5 space-y-5">

        <!-- 드래그앤드롭 업로드 -->
        <div
          class="relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed transition-colors cursor-pointer min-h-[180px]"
          :class="dragging
            ? 'border-bk-yellow bg-bk-yellow/5'
            : 'border-bk-border hover:border-bk-yellow/50 bg-bk-bg'"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
          @click="fileInput?.click()"
        >
          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileChange" />

          <div v-if="uploadedSrc" class="w-full flex flex-col items-center gap-3 p-4">
            <img :src="uploadedSrc" alt="업로드 이미지"
                 class="max-h-44 rounded-lg object-contain shadow" />
            <span class="text-xs text-bk-text-3">{{ uploadedName }}</span>
          </div>
          <template v-else>
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-bk-elevated">
              <i class="fa-solid fa-cloud-arrow-up text-xl text-bk-yellow"></i>
            </div>
            <div class="text-center">
              <p class="text-sm font-medium text-bk-text">이미지를 드래그하거나 클릭하여 업로드</p>
              <p class="mt-1 text-xs text-bk-text-3">JPG · PNG · WEBP · AVIF 지원</p>
            </div>
          </template>
        </div>

        <!-- 분류 버튼 -->
        <button
          :disabled="!uploadedFile || classifying"
          class="btn-yellow w-full py-3 flex items-center justify-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          @click="classify"
        >
          <i v-if="classifying" class="fa-solid fa-spinner fa-spin"></i>
          <i v-else class="fa-solid fa-magnifying-glass"></i>
          {{ classifying ? 'AI 분석 중 (llava:34b)...' : '정품/불량품 검사' }}
        </button>

        <!-- 결과 표시 -->
        <transition name="fade">
          <div v-if="result" class="rounded-xl overflow-hidden border"
               :class="result.result === 'y'
                 ? 'border-green-500/40 bg-green-500/5'
                 : 'border-red-500/40 bg-red-500/5'">
            <div class="flex items-center gap-3 px-5 py-4 border-b"
                 :class="result.result === 'y' ? 'border-green-500/20' : 'border-red-500/20'">
              <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full"
                   :class="result.result === 'y' ? 'bg-green-500/10' : 'bg-red-500/10'">
                <i class="text-xl"
                   :class="result.result === 'y'
                     ? 'fa-solid fa-circle-check text-green-400'
                     : 'fa-solid fa-circle-xmark text-red-400'"></i>
              </div>
              <div>
                <p class="text-lg font-bold"
                   :class="result.result === 'y' ? 'text-green-400' : 'text-red-400'">
                  {{ result.label }}
                </p>
                <p class="text-xs text-bk-text-3">
                  신뢰도 {{ (result.confidence * 100).toFixed(1) }}%
                  &nbsp;·&nbsp;
                  {{ result.method === 'ollama_vision' ? 'llava 비전 분석' : '유사도 분석' }}
                </p>
              </div>
              <div class="ml-auto">
                <div class="h-2 w-24 rounded-full bg-bk-elevated overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-700"
                       :class="result.result === 'y' ? 'bg-green-400' : 'bg-red-400'"
                       :style="{ width: (result.confidence * 100) + '%' }" />
                </div>
              </div>
            </div>
            <div class="px-5 py-4 space-y-2">
              <div class="flex items-start gap-2">
                <i class="fa-solid fa-comment-dots mt-0.5 text-xs text-bk-text-3 flex-shrink-0"></i>
                <p class="text-sm text-bk-text-2">{{ result.reason }}</p>
              </div>
              <div class="flex items-center gap-2 text-xs text-bk-text-3">
                <i class="fa-solid fa-chart-simple"></i>
                <span>이미지 유사도: {{ (result.sim_score * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </transition>

        <!-- 에러 -->
        <div v-if="error" class="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
          <i class="fa-solid fa-triangle-exclamation mr-1.5"></i>{{ error }}
        </div>

      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineComponent, h } from 'vue';

const props = defineProps<{ apiUrl: string; token: string }>();

// ── 타입 ─────────────────────────────────────────────────────────────────────

type TrainingImage = { filename: string; split: string; label: string; base64: string };
type ClassifyResult = {
  result: 'y' | 'n'; label: string; confidence: number;
  reason: string; sim_score: number; method: string;
};
type QualityConfig = {
  trained: boolean;
  similarity_threshold?: number;
  vision_model?: string;
  val_accuracy?: number;
  train_count?: { y: number; n: number };
};

// ── 상태 ─────────────────────────────────────────────────────────────────────

const originalSrc  = ref('');
const config       = ref<QualityConfig>({ trained: false });
const trainImages  = ref<TrainingImage[]>([]);
const valImages    = ref<TrainingImage[]>([]);

const dragging     = ref(false);
const fileInput    = ref<HTMLInputElement | null>(null);
const uploadedFile = ref<File | null>(null);
const uploadedSrc  = ref('');
const uploadedName = ref('');

const classifying  = ref(false);
const progressPct  = ref(0);
const progressMsg  = ref('');
const result       = ref<ClassifyResult | null>(null);
const error        = ref('');

// ── 서브컴포넌트 ─────────────────────────────────────────────────────────────

const StatCard = defineComponent({
  props: { label: String, value: String },
  setup(p) {
    return () => h('div', { class: 'rounded-lg bg-bk-elevated px-3 py-2' }, [
      h('p', { class: 'text-xs text-bk-text-3 mb-0.5' }, p.label),
      h('p', { class: 'text-sm font-semibold text-bk-text truncate' }, p.value ?? '—'),
    ]);
  },
});

const GalleryRow = defineComponent({
  props: {
    label: String,
    items: { type: Array as () => TrainingImage[], default: () => [] },
  },
  setup(p) {
    return () => h('div', [
      h('p', { class: 'text-xs text-bk-text-3 mb-2 font-medium' }, p.label),
      h('div', { class: 'flex flex-wrap gap-2' },
        p.items.map(item =>
          h('div', { key: item.filename, class: 'relative group' }, [
            h('img', {
              src:   `data:image/jpeg;base64,${item.base64}`,
              alt:   item.filename,
              title: item.filename,
              class: 'h-20 w-20 rounded-lg object-cover border-2 cursor-pointer transition-transform group-hover:scale-105',
              style: item.label === 'y'
                ? 'border-color:rgba(74,222,128,0.5)'
                : 'border-color:rgba(248,113,113,0.5)',
            }),
            h('span', {
              class: 'absolute top-1 left-1 rounded text-[10px] font-bold px-1 text-white',
              style: `background:${item.label === 'y' ? 'rgba(34,197,94,0.8)' : 'rgba(239,68,68,0.8)'}`,
            }, item.label.toUpperCase()),
          ])
        )
      ),
    ]);
  },
});

// ── 데이터 로드 ───────────────────────────────────────────────────────────────

async function loadOriginal() {
  try {
    const res = await fetch(`${props.apiUrl}/api/quality/original`);
    if (!res.ok) return;
    const { base64, mimeType } = await res.json();
    originalSrc.value = `data:${mimeType};base64,${base64}`;
  } catch { /* 무시 */ }
}

async function loadConfig() {
  try {
    const res = await fetch(`${props.apiUrl}/api/quality/config`);
    if (res.ok) config.value = await res.json();
  } catch { /* 무시 */ }
}

async function loadTrainingData() {
  try {
    const res = await fetch(`${props.apiUrl}/api/quality/training-data`);
    if (!res.ok) return;
    const data = await res.json();
    trainImages.value = data.train ?? [];
    valImages.value   = data.val   ?? [];
  } catch { /* 무시 */ }
}

onMounted(() => {
  loadOriginal();
  loadConfig();
  loadTrainingData();
});

// ── 파일 업로드 ───────────────────────────────────────────────────────────────

function setFile(file: File) {
  uploadedFile.value = file;
  uploadedName.value = file.name;
  result.value = null;
  error.value  = '';
  const reader = new FileReader();
  reader.onload = (e) => { uploadedSrc.value = e.target?.result as string; };
  reader.readAsDataURL(file);
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (f) setFile(f);
}

function onDrop(e: DragEvent) {
  dragging.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (f && f.type.startsWith('image/')) setFile(f);
}

// ── 분류 ─────────────────────────────────────────────────────────────────────

async function classify() {
  if (!uploadedFile.value) return;
  classifying.value = true;
  error.value       = '';
  result.value      = null;
  progressPct.value = 5;
  progressMsg.value = '이미지 인코딩 중...';

  try {
    const b64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload  = (e) => {
        const full = e.target?.result as string;
        resolve(full.split(',')[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(uploadedFile.value!);
    });

    progressPct.value = 15;
    progressMsg.value = 'llava:34b 비전 모델 호출 중 (30~90초 소요)...';

    // llava 추론 중 프로그레스 바 가상 진행
    const fakeTimer = setInterval(() => {
      if (progressPct.value < 88) progressPct.value += 3;
    }, 2000);

    const res = await fetch(`${props.apiUrl}/api/quality/classify`, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization:  `Bearer ${props.token}`,
      },
      body: JSON.stringify({ base64: b64, mimeType: uploadedFile.value!.type }),
    });

    clearInterval(fakeTimer);
    progressPct.value = 98;
    progressMsg.value = '결과 처리 중...';

    if (!res.ok) {
      const body = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
      throw new Error((body as { message?: string }).message ?? `HTTP ${res.status}`);
    }

    result.value = await res.json();
    progressPct.value = 100;
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    classifying.value = false;
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
