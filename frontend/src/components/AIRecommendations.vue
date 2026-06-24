<template>
  <div class="space-y-4">

    <!-- ── 헤더 배너 ─────────────────────────────────────────────────── -->
    <div class="card-bk overflow-hidden">
      <div class="flex items-center justify-between gap-4 p-6"
           style="background: linear-gradient(135deg, #0F6CBD 0%, #5C2E91 100%);">
        <div class="flex items-center gap-5">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
            <i class="fa-solid fa-robot text-2xl text-white"></i>
          </div>
          <div>
            <p class="text-lg font-bold text-white">AI 투자 비서</p>
            <p class="mt-0.5 text-sm text-white/75">
              포트폴리오를 분석하여 최적 투자 액션 5개를 제안합니다
            </p>
          </div>
        </div>
        <button
          :disabled="loading"
          class="flex flex-shrink-0 items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-bk-yellow shadow hover:bg-bk-elevated transition-colors disabled:opacity-50"
          @click="fetchRecommendations"
        >
          <i v-if="loading" class="fa-solid fa-spinner fa-spin"></i>
          <i v-else class="fa-solid fa-wand-magic-sparkles"></i>
          {{ loading ? 'AI 분석 중...' : 'AI 분석 시작' }}
        </button>
      </div>

      <!-- ── SSE Progress Bar (로딩 시 헤더 하단에 표시) ────────────── -->
      <div v-if="loading" class="border-t border-white/10 bg-[#0a0e1a] px-6 py-4">
        <!-- 단계 레이블 -->
        <div class="mb-3 flex justify-between text-[11px] font-medium">
          <span :class="progressPercent >= 3  ? 'text-bk-yellow' : 'text-white/30'">포트폴리오 로드</span>
          <span :class="progressPercent >= 12 ? 'text-bk-yellow' : 'text-white/30'">모델 초기화</span>
          <span :class="progressPercent >= 15 ? 'text-bk-yellow' : 'text-white/30'">GPU 추론</span>
          <span :class="progressPercent >= 96 ? 'text-bk-yellow' : 'text-white/30'">결과 분석</span>
        </div>

        <!-- 진행 바 -->
        <div class="h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div
            class="h-full rounded-full transition-all duration-700 ease-out"
            style="background: linear-gradient(90deg, #F7B731 0%, #0F6CBD 100%)"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>

        <!-- 메시지 + 퍼센트 -->
        <div class="mt-2.5 flex items-center justify-between">
          <p class="text-xs text-white/60">{{ progressMessage }}</p>
          <span class="text-xs font-semibold text-bk-yellow">{{ progressPercent }}%</span>
        </div>
      </div>
    </div>

    <!-- ── 에러 ──────────────────────────────────────────────────────── -->
    <div v-if="error" class="card-bk flex items-center gap-3 p-4 text-sm text-red-600 border-red-200">
      <i class="fa-solid fa-triangle-exclamation text-red-400"></i>
      {{ error }}
    </div>

    <!-- ── 빈 상태 ────────────────────────────────────────────────────── -->
    <div v-if="!loading && !error && recommendations.length === 0"
      class="card-bk flex flex-col items-center justify-center py-20">
      <div class="flex h-20 w-20 items-center justify-center rounded-full bg-bk-elevated">
        <i class="fa-solid fa-robot text-4xl text-bk-text-3"></i>
      </div>
      <p class="mt-5 font-semibold text-bk-text">추천 일정이 없습니다</p>
      <p class="mt-1 text-sm text-bk-text-3">위의 "AI 분석 시작" 버튼을 눌러 추천을 받아보세요</p>
    </div>

    <!-- ── 추천 카드 목록 ─────────────────────────────────────────────── -->
    <div v-if="!loading && recommendations.length > 0" class="space-y-3">
      <div
        v-for="(rec, idx) in recommendations"
        :key="idx"
        class="card-bk transition-shadow hover:shadow-lifted"
      >
        <!-- 카드 헤더 -->
        <div class="flex items-center justify-between gap-4 border-b border-bk-border px-5 py-4">
          <div class="flex items-center gap-4">
            <span
              class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl text-sm font-bold"
              :style="{ color: actionColor(rec.action), background: `${actionColor(rec.action)}15` }"
            >
              <i :class="actionIcon(rec.action)"></i>
            </span>

            <div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold text-bk-text">{{ rec.asset_name }}</span>
                <span class="font-mono text-xs text-bk-text-3 bg-bk-elevated px-1.5 py-0.5 rounded">{{ rec.ticker }}</span>
                <span
                  class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  :style="{ color: actionColor(rec.action), background: `${actionColor(rec.action)}15` }"
                >{{ rec.category }}</span>
                <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="priorityClass(rec.priority)">
                  {{ rec.priority }}
                </span>
                <span v-if="scheduled.has(idx)"
                  class="flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  style="color:#107C10; background: rgba(16,124,16,0.10);">
                  <i class="fa-solid fa-circle-check"></i> 등록됨
                </span>
              </div>
              <p class="mt-0.5 text-sm text-bk-text-2">
                추천 일정 &nbsp;<span class="font-mono font-semibold text-bk-yellow">{{ rec.suggested_date }}</span>
              </p>
            </div>
          </div>

          <button
            v-if="!scheduled.has(idx)"
            :disabled="scheduling === idx"
            class="btn-ghost flex flex-shrink-0 items-center gap-2 px-4 py-2 text-sm"
            @click="scheduleEvent(rec, idx)"
          >
            <i v-if="scheduling === idx" class="fa-solid fa-spinner fa-spin"></i>
            <i v-else class="fa-solid fa-calendar-plus"></i>
            {{ scheduling === idx ? '저장 중...' : '일정 추가' }}
          </button>
        </div>

        <!-- 추천 이유 -->
        <div class="px-5 py-4 bg-bk-elevated/50">
          <p class="label-caps mb-2">추천 근거</p>
          <p class="text-sm leading-relaxed text-bk-text-2">{{ rec.reason }}</p>
        </div>
      </div>

      <!-- 전체 일정 등록 -->
      <div class="flex items-center justify-between rounded-lg border border-bk-border bg-white p-4">
        <p class="text-sm text-bk-text-2">
          <span class="font-semibold text-bk-yellow">{{ scheduled.size }}</span>
          / {{ recommendations.length }} 등록됨
        </p>
        <button
          :disabled="allScheduled || bulkScheduling"
          class="btn-yellow flex items-center gap-2 px-5 py-2.5 text-sm"
          @click="scheduleAll"
        >
          <i v-if="bulkScheduling" class="fa-solid fa-spinner fa-spin"></i>
          <i v-else class="fa-solid fa-calendar-check"></i>
          {{ bulkScheduling ? '등록 중...' : allScheduled ? '모두 등록됨' : '전체 일정에 추가' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

type Recommendation = {
  ticker: string; asset_name: string; action: string;
  category: string; reason: string; suggested_date: string; priority: string;
};

const props = defineProps<{ apiUrl: string; token: string }>();
const emit = defineEmits<{ (e: 'event-added'): void }>();

const loading         = ref(false);
const error           = ref('');
const recommendations = ref<Recommendation[]>([]);
const scheduled       = ref<Set<number>>(new Set());
const scheduling      = ref<number | null>(null);
const bulkScheduling  = ref(false);
const progressPercent = ref(0);
const progressMessage = ref('');

const allScheduled = computed(
  () => recommendations.value.length > 0 && scheduled.value.size === recommendations.value.length,
);

// SSE 스트림으로 AI 추천을 받아온다.
// fetch + ReadableStream 으로 구현 — EventSource는 커스텀 헤더를 지원하지 않아 사용 불가.
async function fetchRecommendations() {
  loading.value         = true;
  error.value           = '';
  recommendations.value = [];
  scheduled.value       = new Set();
  progressPercent.value = 0;
  progressMessage.value = 'AI 분석을 시작합니다...';

  try {
    const res = await fetch(`${props.apiUrl}/api/ai/recommend/stream`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${props.token}` },
    });

    if (!res.ok || !res.body) {
      const msg = res.body ? (await res.json()).message : `HTTP ${res.status}`;
      throw new Error(msg);
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      // SSE는 \n\n 으로 이벤트를 구분하지만, 청크 경계에서 잘릴 수 있어
      // \n 단위로 처리하고 마지막 불완전 라인은 buffer 에 보존한다.
      const lines = buffer.split('\n');
      buffer = lines.pop()!;

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const event = JSON.parse(line.slice(6));

        if (event.type === 'progress') {
          progressPercent.value = event.percent;
          progressMessage.value = event.message;
        } else if (event.type === 'done') {
          progressPercent.value = 100;
          progressMessage.value = '완료';
          recommendations.value = event.recommendations ?? [];
        } else if (event.type === 'error') {
          throw new Error(event.message);
        }
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'AI 추천 요청 실패';
  } finally {
    loading.value = false;
  }
}

async function addToCalendar(rec: Recommendation) {
  const typeMap: Record<string, string> = {
    BUY: 'buy', SELL: 'sell', REBALANCE: 'rebalance', WATCH: 'watch',
  };
  const start = new Date(`${rec.suggested_date}T10:00:00`);
  const end   = new Date(`${rec.suggested_date}T11:00:00`);
  const res = await fetch(`${props.apiUrl}/api/calendar/events`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${props.token}` },
    body: JSON.stringify({
      title:            `[AI] ${rec.asset_name} ${rec.category}`,
      event_type:       typeMap[rec.action] ?? 'general',
      ticker:           rec.ticker,
      start:            start.toISOString(),
      end:              end.toISOString(),
      notes:            rec.reason,
      is_ai_recommended: true,
      priority:         rec.priority,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).message);
}

async function scheduleEvent(rec: Recommendation, idx: number) {
  scheduling.value = idx;
  try {
    await addToCalendar(rec);
    scheduled.value = new Set([...scheduled.value, idx]);
    emit('event-added');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '일정 추가 실패';
  } finally {
    scheduling.value = null;
  }
}

async function scheduleAll() {
  bulkScheduling.value = true;
  error.value = '';
  try {
    for (let i = 0; i < recommendations.value.length; i++) {
      if (!scheduled.value.has(i)) {
        await addToCalendar(recommendations.value[i]);
        scheduled.value = new Set([...scheduled.value, i]);
      }
    }
    emit('event-added');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '일정 추가 중 오류';
  } finally {
    bulkScheduling.value = false;
  }
}

const ACTION_COLORS: Record<string, string> = {
  BUY: '#107C10', SELL: '#D13438', REBALANCE: '#5C2E91', WATCH: '#008272',
};
function actionColor(a: string) { return ACTION_COLORS[a] ?? '#605E5C'; }
function actionIcon(a: string) {
  return ({ BUY:'fa-solid fa-arrow-trend-up', SELL:'fa-solid fa-arrow-trend-down',
            REBALANCE:'fa-solid fa-scale-balanced', WATCH:'fa-solid fa-eye' } as Record<string,string>)[a]
    ?? 'fa-solid fa-circle-dot';
}
function priorityClass(p: string) {
  return ({
    HIGH:   'bg-red-50 text-red-700 border border-red-200',
    MEDIUM: 'bg-amber-50 text-amber-700 border border-amber-200',
    LOW:    'bg-bk-elevated text-bk-text-3',
  } as Record<string,string>)[p] ?? 'bg-bk-elevated text-bk-text-3';
}
</script>
