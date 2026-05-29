<template>
  <div class="space-y-4">

    <!-- ── 상단 툴바 ───────────────────────────────────────────────────── -->
    <div class="card-bk px-5 py-3 space-y-3">
      <!-- 범례 -->
      <div class="flex flex-wrap items-center gap-2">
        <span v-for="c in calendarList" :key="c.id"
          class="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-full"
          :style="{ color: c.color, border: `1px solid ${c.color}44`, background: `${c.color}12` }">
          <i :class="c.icon" class="text-xs"></i>{{ c.name }}
        </span>
      </div>
      <!-- 일정 추가 -->
      <div class="flex justify-end">
        <button class="btn-yellow flex items-center gap-2 px-4 py-2 text-sm" @click="showAddModal = true">
          <i class="fa-solid fa-calendar-plus"></i> 일정 추가
        </button>
      </div>
    </div>

    <!-- ── 캘린더 컨테이너 ─────────────────────────────────────────────── -->
    <div class="card-bk overflow-hidden">
      <!-- 네비게이션 헤더 -->
      <div class="flex items-center justify-between border-b border-bk-border px-5 py-3 bg-bk-elevated">
        <button class="btn-ghost px-3 py-1.5 text-sm" @click="movePrev">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span class="font-semibold text-bk-text text-base">{{ currentTitle }}</span>
        <button class="btn-ghost px-3 py-1.5 text-sm" @click="moveNext">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
      <div ref="calendarEl" class="min-h-[600px]"></div>
    </div>

    <!-- ── 일정 추가 모달 ─────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div class="card-bk w-full max-w-lg shadow-xl">

          <!-- 모달 헤더 -->
          <div class="flex items-center justify-between border-b border-bk-border px-6 py-4 bg-bk-elevated">
            <p class="font-semibold text-bk-text">금융 일정 추가</p>
            <button class="text-bk-text-3 hover:text-bk-text" @click="showAddModal = false">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>

          <!-- 모달 본문 -->
          <form class="space-y-4 px-6 py-5" @submit.prevent="submitAdd">
            <div>
              <label class="label-caps mb-2 block">제목 *</label>
              <input v-model="form.title" class="input-bk" placeholder="예: 삼성전자 추가 매수" required />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label-caps mb-2 block">이벤트 유형</label>
                <select v-model="form.event_type" class="input-bk">
                  <optgroup label="매매">
                    <option value="buy">매수</option>
                    <option value="sell">매도</option>
                    <option value="rebalance">리밸런싱</option>
                    <option value="rights">유상증자</option>
                    <option value="ipo">공모 청약</option>
                  </optgroup>
                  <optgroup label="수익">
                    <option value="dividend">배당</option>
                    <option value="bond">채권/이자</option>
                  </optgroup>
                  <optgroup label="분석/모니터링">
                    <option value="earnings">실적발표</option>
                    <option value="macro">거시경제 지표</option>
                    <option value="watch">모니터링</option>
                    <option value="fx">환율/외환</option>
                  </optgroup>
                  <optgroup label="기타">
                    <option value="tax">세금/신고</option>
                    <option value="general">일반</option>
                  </optgroup>
                </select>
              </div>
              <div>
                <label class="label-caps mb-2 block">우선순위</label>
                <select v-model="form.priority" class="input-bk">
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
            </div>

            <div>
              <label class="label-caps mb-2 block">티커 / 지수 (선택)</label>
              <input v-model="form.ticker" class="input-bk font-mono" placeholder="예: 005930, SPX, USD/KRW" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label-caps mb-2 block">시작일시 *</label>
                <input v-model="form.start" type="datetime-local" class="input-bk text-sm" required />
              </div>
              <div>
                <label class="label-caps mb-2 block">종료일시 *</label>
                <input v-model="form.end" type="datetime-local" class="input-bk text-sm" required />
              </div>
            </div>

            <div>
              <label class="label-caps mb-2 block">메모</label>
              <textarea v-model="form.notes" class="input-bk resize-none" rows="2"
                placeholder="투자 근거, 목표가, 지표 예상치 등"></textarea>
            </div>

            <p v-if="formError" class="flex items-center gap-1.5 text-sm text-red-500">
              <i class="fa-solid fa-circle-exclamation"></i>{{ formError }}
            </p>

            <div class="flex gap-3 border-t border-bk-border pt-4">
              <button type="button" class="btn-ghost flex-1 py-2.5 text-sm" @click="showAddModal = false">
                취소
              </button>
              <button type="submit" :disabled="submitting" class="btn-yellow flex-1 flex items-center justify-center gap-2 py-2.5 text-sm">
                <i v-if="submitting" class="fa-solid fa-spinner fa-spin"></i>
                {{ submitting ? '저장 중...' : '저장' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import Calendar from 'tui-calendar';
import 'tui-calendar/dist/tui-calendar.css';

type InvestmentEvent = {
  id: number; title: string; event_type: string; ticker: string;
  start: string; end: string; notes: string;
  is_ai_recommended: boolean; priority: string; status: string;
};

const props = defineProps<{ events: InvestmentEvent[]; apiUrl: string; token: string }>();
const emit = defineEmits<{ (e: 'event-added'): void }>();

const calendarEl = ref<HTMLDivElement | null>(null);
let calendar: Calendar | null = null;
const currentTitle = ref('');
const showAddModal = ref(false);
const submitting = ref(false);
const formError = ref('');

const form = reactive({
  title: '', event_type: 'buy', ticker: '',
  start: '', end: '', notes: '', priority: 'MEDIUM',
});

const calendarList = [
  { id:'buy',       name:'매수',        color:'#16A34A', icon:'fa-solid fa-arrow-trend-up' },
  { id:'sell',      name:'매도',        color:'#DC2626', icon:'fa-solid fa-arrow-trend-down' },
  { id:'dividend',  name:'배당',        color:'#2563EB', icon:'fa-solid fa-money-bill-wave' },
  { id:'earnings',  name:'실적발표',    color:'#EA580C', icon:'fa-solid fa-chart-bar' },
  { id:'rebalance', name:'리밸런싱',    color:'#7C3AED', icon:'fa-solid fa-scale-balanced' },
  { id:'watch',     name:'모니터링',    color:'#0891B2', icon:'fa-solid fa-eye' },
  { id:'ipo',       name:'공모 청약',   color:'#DB2777', icon:'fa-solid fa-rocket' },
  { id:'macro',     name:'거시경제',    color:'#0F766E', icon:'fa-solid fa-landmark' },
  { id:'tax',       name:'세금/신고',   color:'#D97706', icon:'fa-solid fa-file-invoice-dollar' },
  { id:'rights',    name:'유상증자',    color:'#0369A1', icon:'fa-solid fa-circle-plus' },
  { id:'bond',      name:'채권/금리',   color:'#475569', icon:'fa-solid fa-percent' },
  { id:'fx',        name:'환율/외환',   color:'#6D28D9', icon:'fa-solid fa-arrows-rotate' },
  { id:'general',   name:'일반',        color:'#64748B', icon:'fa-solid fa-circle-dot' },
];

function toSchedules(events: InvestmentEvent[]) {
  return events.map(e => {
    const cal = calendarList.find(c => c.id === e.event_type) ?? calendarList[calendarList.length - 1];
    return {
      id: String(e.id),
      calendarId: cal.id,
      title: e.ticker ? `[${e.ticker}] ${e.title}` : e.title,
      category: 'time',
      start: e.start,
      end: e.end,
      body: e.notes,
    };
  });
}

function updateTitle() {
  if (!calendar) return;
  const d = calendar.getDate() as unknown as Date;
  currentTitle.value = `${d.getFullYear()}년 ${d.getMonth() + 1}월`;
}

function movePrev() { calendar?.prev(); updateTitle(); }
function moveNext() { calendar?.next(); updateTitle(); }

onMounted(() => {
  if (!calendarEl.value) return;
  calendar = new Calendar(calendarEl.value, {
    defaultView: 'month',
    taskView: false,
    scheduleView: ['time'],
    calendars: calendarList.map(c => ({
      id: c.id, name: c.name,
      color: '#FFFFFF', bgColor: c.color, borderColor: c.color,
    })),
    template: {
      monthDayname: d =>
        `<span style="color:#94A3B8;font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">${d.label}</span>`,
    },
  });
  calendar.createSchedules(toSchedules(props.events));
  updateTitle();
});

watch(() => props.events, evs => {
  if (!calendar) return;
  calendar.clear();
  calendar.createSchedules(toSchedules(evs));
}, { deep: true });

onBeforeUnmount(() => { calendar?.destroy(); calendar = null; });

async function submitAdd() {
  formError.value = '';
  submitting.value = true;
  try {
    const res = await fetch(`${props.apiUrl}/api/calendar/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${props.token}` },
      body: JSON.stringify({
        title: form.title, event_type: form.event_type,
        ticker: form.ticker || null,
        start: new Date(form.start).toISOString(),
        end: new Date(form.end).toISOString(),
        notes: form.notes || null, priority: form.priority,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).message);
    showAddModal.value = false;
    Object.assign(form, { title:'', event_type:'buy', ticker:'', start:'', end:'', notes:'', priority:'MEDIUM' });
    emit('event-added');
  } catch (err) {
    formError.value = err instanceof Error ? err.message : '저장 실패';
  } finally {
    submitting.value = false;
  }
}
</script>
