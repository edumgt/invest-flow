<template>
  <div class="space-y-4">

    <!-- 헤더 툴바 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-sm text-bk-text-3">
        <i class="fa-solid fa-server text-xs"></i>
        <span>{{ airflowUrl }}</span>
        <span class="inline-block h-2 w-2 rounded-full"
              :class="health === 'healthy' ? 'bg-green-400' : health === 'loading' ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'"></span>
        <span>{{ health }}</span>
      </div>
      <button class="flex items-center gap-1.5 rounded-lg border border-bk-border px-3 py-1.5 text-xs text-bk-text-2 hover:border-bk-yellow hover:text-bk-yellow transition-colors"
              :class="{ 'animate-pulse': refreshing }" @click="refresh">
        <i class="fa-solid fa-rotate-right text-xs" :class="{ 'fa-spin': refreshing }"></i>
        새로고침
      </button>
    </div>

    <!-- DAG 목록 -->
    <div v-for="dag in dags" :key="dag.dag_id" class="card-bk overflow-hidden">

      <!-- DAG 헤더 -->
      <div class="flex items-center gap-3 border-b border-bk-border px-5 py-3"
           :class="expandedDag === dag.dag_id ? 'bg-bk-elevated' : ''">

        <!-- 상태 표시등 -->
        <div class="h-2 w-2 flex-shrink-0 rounded-full"
             :class="dag.is_paused ? 'bg-bk-text-3' : 'bg-green-400'"></div>

        <!-- DAG ID + 설명 -->
        <div class="min-w-0 flex-1 cursor-pointer" @click="toggleDag(dag.dag_id)">
          <p class="truncate text-sm font-semibold text-bk-text">{{ dag.dag_id }}</p>
          <p v-if="dag.description" class="truncate text-xs text-bk-text-3">{{ dag.description }}</p>
          <div class="mt-0.5 flex flex-wrap gap-2">
            <span class="text-xs text-bk-text-3">
              <i class="fa-regular fa-clock mr-1"></i>{{ dag.schedule_interval?.value ?? dag.timetable_description ?? '없음' }}
            </span>
            <span v-if="dag.tags?.length" class="text-xs text-bk-text-3">
              <i class="fa-solid fa-tag mr-1"></i>{{ dag.tags.map((t:any) => t.name).join(', ') }}
            </span>
          </div>
        </div>

        <!-- 액션 버튼 -->
        <div class="flex items-center gap-2 flex-shrink-0">
          <!-- 일시정지 토글 -->
          <button
            :title="dag.is_paused ? 'DAG 재개' : 'DAG 일시정지'"
            class="rounded px-2 py-1 text-xs transition-colors"
            :class="dag.is_paused
              ? 'border border-green-500/30 text-green-400 hover:bg-green-500/10'
              : 'border border-bk-border text-bk-text-3 hover:border-yellow-500/30 hover:text-yellow-400'"
            @click="togglePause(dag)"
          >
            <i :class="dag.is_paused ? 'fa-solid fa-play' : 'fa-solid fa-pause'"></i>
          </button>

          <!-- 수동 트리거 -->
          <button
            title="DAG 수동 실행"
            class="rounded border border-bk-yellow/30 px-2 py-1 text-xs text-bk-yellow hover:bg-bk-yellow/10 transition-colors"
            :class="{ 'opacity-50 cursor-not-allowed': triggering[dag.dag_id] }"
            :disabled="triggering[dag.dag_id]"
            @click="trigger(dag.dag_id)"
          >
            <i class="fa-solid fa-play" :class="{ 'fa-spin fa-gear': triggering[dag.dag_id] }"></i>
            {{ triggering[dag.dag_id] ? '실행 중...' : '실행' }}
          </button>

          <!-- 펼치기 -->
          <button class="text-bk-text-3 hover:text-bk-yellow transition-colors px-1"
                  @click="toggleDag(dag.dag_id)">
            <i class="fa-solid text-xs"
               :class="expandedDag === dag.dag_id ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
          </button>
        </div>
      </div>

      <!-- 런 히스토리 (펼쳐진 상태) -->
      <div v-if="expandedDag === dag.dag_id">

        <!-- 로딩 -->
        <div v-if="runsLoading[dag.dag_id]" class="flex items-center gap-2 px-5 py-4 text-sm text-bk-text-3">
          <i class="fa-solid fa-spinner fa-spin text-xs"></i> 런 히스토리 로딩 중...
        </div>

        <!-- 런 없음 -->
        <div v-else-if="!runs[dag.dag_id]?.length"
             class="px-5 py-4 text-sm text-bk-text-3">
          실행 기록이 없습니다.
        </div>

        <!-- 런 테이블 -->
        <div v-else>
          <div v-for="run in runs[dag.dag_id]" :key="run.dag_run_id"
               class="border-b border-bk-border last:border-0">

            <!-- 런 행 -->
            <div class="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-bk-elevated transition-colors"
                 @click="toggleRun(dag.dag_id, run.dag_run_id)">

              <!-- 상태 배지 -->
              <RunBadge :state="run.state" />

              <!-- 런 정보 -->
              <div class="min-w-0 flex-1">
                <p class="truncate text-xs font-mono text-bk-text-2">{{ run.dag_run_id }}</p>
                <p class="text-xs text-bk-text-3">
                  {{ formatDate(run.start_date) }}
                  <span v-if="run.end_date" class="ml-1">
                    · {{ duration(run.start_date, run.end_date) }}
                  </span>
                  <span class="ml-1 capitalize text-bk-text-3">· {{ run.run_type }}</span>
                </p>
              </div>

              <i class="fa-solid text-xs text-bk-text-3 flex-shrink-0"
                 :class="expandedRun === run.dag_run_id ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
            </div>

            <!-- 태스크 인스턴스 -->
            <div v-if="expandedRun === run.dag_run_id"
                 class="border-t border-bk-border bg-bk-bg px-5 py-3">

              <div v-if="tasksLoading[run.dag_run_id]"
                   class="text-xs text-bk-text-3 flex items-center gap-2">
                <i class="fa-solid fa-spinner fa-spin"></i> 태스크 로딩 중...
              </div>

              <div v-else class="space-y-1.5">
                <div v-for="task in tasks[run.dag_run_id]" :key="task.task_id"
                     class="flex items-center gap-3 rounded-lg px-3 py-2 bg-bk-surface">
                  <RunBadge :state="task.state" size="sm" />
                  <span class="flex-1 font-mono text-xs text-bk-text">{{ task.task_id }}</span>
                  <span v-if="task.duration != null" class="text-xs text-bk-text-3">
                    {{ task.duration.toFixed(1) }}s
                  </span>
                  <span v-if="task.start_date" class="text-xs text-bk-text-3">
                    {{ formatDate(task.start_date) }}
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>

    <!-- DAG 없음 -->
    <div v-if="!loading && !dags.length"
         class="card-bk px-6 py-10 text-center text-sm text-bk-text-3">
      <i class="fa-solid fa-database text-2xl mb-3 block"></i>
      DAG를 찾을 수 없습니다.
    </div>

    <!-- 전체 로딩 -->
    <div v-if="loading" class="card-bk px-6 py-10 text-center text-sm text-bk-text-3">
      <i class="fa-solid fa-spinner fa-spin text-2xl mb-3 block text-bk-yellow"></i>
      Airflow 정보를 가져오는 중...
    </div>

    <!-- 에러 -->
    <div v-if="error"
         class="card-bk border border-red-500/30 px-5 py-4 text-sm text-red-400">
      <i class="fa-solid fa-triangle-exclamation mr-1.5"></i>{{ error }}
    </div>

    <!-- 트리거 결과 토스트 -->
    <transition name="slide-up">
      <div v-if="toast"
           class="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm shadow-lifted"
           :class="toast.type === 'success'
             ? 'border-green-500/30 bg-bk-surface text-green-400'
             : 'border-red-500/30 bg-bk-surface text-red-400'">
        <i :class="toast.type === 'success' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
        {{ toast.message }}
      </div>
    </transition>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, defineComponent, h } from 'vue';

const props = defineProps<{ apiUrl: string; token: string }>();

// ── 상수 ─────────────────────────────────────────────────────────────────────

const airflowUrl = 'Airflow @ 192.168.253.149:8793';
const POLL_MS    = 30_000;  // 30초 자동 갱신

// ── 상태 ─────────────────────────────────────────────────────────────────────

const health      = ref<'loading'|'healthy'|'unhealthy'>('loading');
const loading     = ref(true);
const refreshing  = ref(false);
const error       = ref('');
const dags        = ref<Dag[]>([]);
const runs        = ref<Record<string, Run[]>>({});
const tasks       = ref<Record<string, Task[]>>({});
const runsLoading = ref<Record<string, boolean>>({});
const tasksLoading= ref<Record<string, boolean>>({});
const triggering  = ref<Record<string, boolean>>({});
const expandedDag = ref<string | null>(null);
const expandedRun = ref<string | null>(null);
const toast       = ref<{ type: 'success'|'error'; message: string } | null>(null);

type Dag  = { dag_id: string; is_paused: boolean; description?: string; schedule_interval?: {value:string}; timetable_description?: string; tags?: {name:string}[] };
type Run  = { dag_run_id: string; state: string; start_date: string; end_date?: string; run_type: string };
type Task = { task_id: string; state: string; duration?: number; start_date?: string };

// ── 서브컴포넌트: 상태 배지 ───────────────────────────────────────────────────

const STATE_STYLE: Record<string, { bg: string; text: string; icon: string }> = {
  success:  { bg: 'bg-green-500/10',  text: 'text-green-400',  icon: 'fa-circle-check' },
  failed:   { bg: 'bg-red-500/10',    text: 'text-red-400',    icon: 'fa-circle-xmark' },
  running:  { bg: 'bg-blue-500/10',   text: 'text-blue-400',   icon: 'fa-spinner fa-spin' },
  queued:   { bg: 'bg-yellow-500/10', text: 'text-yellow-400', icon: 'fa-clock' },
  skipped:  { bg: 'bg-gray-500/10',   text: 'text-gray-400',   icon: 'fa-forward' },
  upstream_failed: { bg: 'bg-orange-500/10', text: 'text-orange-400', icon: 'fa-arrow-up' },
};

const RunBadge = defineComponent({
  props: {
    state: { type: String, default: 'none' },
    size:  { type: String, default: 'md' },
  },
  setup(p) {
    return () => {
      const s = STATE_STYLE[p.state] ?? { bg: 'bg-bk-elevated', text: 'text-bk-text-3', icon: 'fa-circle' };
      const isSmall = p.size === 'sm';
      return h('span', {
        class: `inline-flex items-center gap-1 rounded-full font-medium capitalize ${s.bg} ${s.text} ${isSmall ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs'}`,
      }, [
        h('i', { class: `fa-solid ${s.icon} ${isSmall ? 'text-[9px]' : 'text-[10px]'}` }),
        p.state,
      ]);
    };
  },
});

// ── API 호출 헬퍼 ─────────────────────────────────────────────────────────────

async function af<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${props.apiUrl}/api/airflow${path}`, {
    ...options,
    headers: {
      Authorization:  `Bearer ${props.token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { message?: string };
    throw new Error(err.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── 데이터 로드 ───────────────────────────────────────────────────────────────

async function loadDags() {
  try {
    const data = await af<{ dags: Dag[] }>('/dags');
    dags.value = data.dags ?? [];
    health.value = 'healthy';
  } catch (e: unknown) {
    health.value = 'unhealthy';
    error.value = e instanceof Error ? e.message : String(e);
  }
}

async function loadRuns(dagId: string) {
  runsLoading.value[dagId] = true;
  try {
    const data = await af<{ dag_runs: Run[] }>(`/dags/${dagId}/runs?limit=8`);
    runs.value[dagId] = data.dag_runs ?? [];
  } catch { /* 무시 */ }
  finally { runsLoading.value[dagId] = false; }
}

async function loadTasks(dagId: string, runId: string) {
  tasksLoading.value[runId] = true;
  try {
    const data = await af<{ task_instances: Task[] }>(`/dags/${dagId}/runs/${encodeURIComponent(runId)}/tasks`);
    tasks.value[runId] = data.task_instances ?? [];
  } catch { /* 무시 */ }
  finally { tasksLoading.value[runId] = false; }
}

async function refresh() {
  refreshing.value = true;
  await loadDags();
  if (expandedDag.value) await loadRuns(expandedDag.value);
  refreshing.value = false;
}

// ── UI 인터랙션 ───────────────────────────────────────────────────────────────

async function toggleDag(dagId: string) {
  if (expandedDag.value === dagId) {
    expandedDag.value = null;
    expandedRun.value = null;
  } else {
    expandedDag.value = dagId;
    expandedRun.value = null;
    if (!runs.value[dagId]) await loadRuns(dagId);
  }
}

async function toggleRun(dagId: string, runId: string) {
  if (expandedRun.value === runId) {
    expandedRun.value = null;
  } else {
    expandedRun.value = runId;
    if (!tasks.value[runId]) await loadTasks(dagId, runId);
  }
}

async function trigger(dagId: string) {
  if (triggering.value[dagId]) return;
  triggering.value[dagId] = true;
  try {
    await af(`/dags/${dagId}/trigger`, { method: 'POST' });
    showToast('success', `${dagId} 실행 요청 완료`);
    setTimeout(() => loadRuns(dagId), 2000);
  } catch (e: unknown) {
    showToast('error', e instanceof Error ? e.message : '실행 실패');
  } finally {
    triggering.value[dagId] = false;
  }
}

async function togglePause(dag: Dag) {
  const action = dag.is_paused ? 'unpause' : 'pause';
  try {
    await af(`/dags/${dag.dag_id}/${action}`, { method: 'POST' });
    dag.is_paused = !dag.is_paused;
    showToast('success', `${dag.dag_id} ${dag.is_paused ? '일시정지' : '재개'}`);
  } catch (e: unknown) {
    showToast('error', e instanceof Error ? e.message : '변경 실패');
  }
}

// ── 유틸 ─────────────────────────────────────────────────────────────────────

function formatDate(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getMonth()+1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function duration(start?: string, end?: string) {
  if (!start || !end) return '';
  const s = (new Date(end).getTime() - new Date(start).getTime()) / 1000;
  if (s < 60)  return `${s.toFixed(0)}s`;
  if (s < 3600) return `${Math.floor(s/60)}m ${(s%60).toFixed(0)}s`;
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
}

let toastTimer: ReturnType<typeof setTimeout> | null = null;
function showToast(type: 'success'|'error', message: string) {
  toast.value = { type, message };
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.value = null; }, 3000);
}

// ── 라이프사이클 ─────────────────────────────────────────────────────────────

let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  await loadDags();
  loading.value = false;
  pollTimer = setInterval(() => {
    loadDags();
    if (expandedDag.value) loadRuns(expandedDag.value);
  }, POLL_MS);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  if (toastTimer) clearTimeout(toastTimer);
});
</script>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: opacity 0.25s, transform 0.25s; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(12px); }
</style>
