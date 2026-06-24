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

    <!-- ── 로딩 스켈레톤 ─────────────────────────────────────────────── -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 5" :key="i" class="card-bk animate-pulse p-5">
        <div class="flex items-center gap-4">
          <div class="h-12 w-12 rounded-xl bg-bk-elevated"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 w-2/5 rounded-full bg-bk-elevated"></div>
            <div class="h-3 w-1/4 rounded-full bg-bk-elevated"></div>
          </div>
        </div>
        <div class="mt-4 space-y-2">
          <div class="h-3 rounded-full bg-bk-elevated"></div>
          <div class="h-3 w-4/5 rounded-full bg-bk-elevated"></div>
        </div>
      </div>
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

const loading = ref(false);
const error = ref('');
const recommendations = ref<Recommendation[]>([]);
const scheduled = ref<Set<number>>(new Set());
const scheduling = ref<number | null>(null);
const bulkScheduling = ref(false);

const allScheduled = computed(
  () => recommendations.value.length > 0 && scheduled.value.size === recommendations.value.length,
);

async function fetchRecommendations() {
  loading.value = true;
  error.value = '';
  recommendations.value = [];
  scheduled.value = new Set();
  try {
    const res = await fetch(`${props.apiUrl}/api/ai/recommend`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${props.token}` },
    });
    if (!res.ok) throw new Error((await res.json()).message);
    const data = await res.json();
    recommendations.value = data.recommendations ?? [];
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
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${props.token}` },
    body: JSON.stringify({
      title: `[AI] ${rec.asset_name} ${rec.category}`,
      event_type: typeMap[rec.action] ?? 'general',
      ticker: rec.ticker,
      start: start.toISOString(),
      end: end.toISOString(),
      notes: rec.reason,
      is_ai_recommended: true,
      priority: rec.priority,
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
