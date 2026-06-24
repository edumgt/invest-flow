<template>
  <!-- ── 로그인 ────────────────────────────────────────────────────────── -->
  <div v-if="!token" class="flex min-h-screen flex-col items-center justify-center bg-bk-bg px-4">
    <div class="w-full max-w-sm">
      <!-- 로고 -->
      <div class="mb-8 text-center">
        <div class="inline-flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-bk-yellow shadow-lifted">
            <i class="fa-solid fa-chart-line text-white text-lg"></i>
          </div>
          <span class="text-2xl font-bold tracking-tight text-bk-text">Invest<span class="text-bk-yellow">Flow</span></span>
        </div>
        <p class="mt-2 text-sm text-bk-text-3">AI 기반 개인 금융 일정 관리</p>
      </div>

      <!-- 로그인 카드 -->
      <div class="card-bk p-8 shadow-lifted">
        <p class="mb-5 text-base font-semibold text-bk-text">로그인</p>
        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="mb-1.5 block text-sm text-bk-text-2">아이디</label>
            <input v-model="username" class="input-bk" placeholder="아이디를 입력하세요" autocomplete="username" />
          </div>
          <div>
            <label class="mb-1.5 block text-sm text-bk-text-2">비밀번호</label>
            <input v-model="password" type="password" class="input-bk" placeholder="비밀번호를 입력하세요" autocomplete="current-password" />
          </div>
          <button
            type="submit"
            :disabled="loginLoading"
            class="btn-yellow mt-2 flex w-full items-center justify-center gap-2 py-3 text-sm"
          >
            <i v-if="loginLoading" class="fa-solid fa-spinner fa-spin"></i>
            <i v-else class="fa-solid fa-arrow-right-to-bracket"></i>
            {{ loginLoading ? '인증 중...' : '로그인' }}
          </button>
        </form>
        <p v-if="loginError" class="mt-3 flex items-center gap-1.5 text-sm text-red-500">
          <i class="fa-solid fa-circle-exclamation"></i>{{ loginError }}
        </p>
        <div class="mt-6 border-t border-bk-border pt-4 text-center text-xs text-bk-text-3">
          테스트 계정 &nbsp;·&nbsp; ID: <span class="text-bk-text-2 font-mono font-semibold">test1</span>
          &nbsp;/&nbsp; PW: <span class="text-bk-text-2 font-mono font-semibold">123456</span>
        </div>
      </div>

      <!-- 로그인 페이지 Footer -->
      <div class="mt-8 flex flex-col items-center gap-1.5">
        <a href="https://www.edumgt.co.kr" target="_blank" rel="noopener"
           class="flex items-center gap-2 text-bk-text-3 hover:text-bk-yellow transition-colors">
          <span class="text-xs font-semibold tracking-wide">(주)에듀엠지티</span>
          <span class="text-xs text-bk-text-3">·</span>
          <span class="text-xs">www.edumgt.co.kr</span>
        </a>
        <p class="text-xs text-bk-text-3">© 2025 EduMGT Co., Ltd. All rights reserved.</p>
      </div>
    </div>
  </div>

  <!-- ── 메인 앱 ────────────────────────────────────────────────────────── -->
  <div v-else class="flex h-screen overflow-hidden bg-bk-bg">

    <!-- 사이드바 (데스크톱) -->
    <aside class="hidden w-60 flex-shrink-0 flex-col border-r border-bk-border bg-bk-surface md:flex shadow-card">
      <!-- 로고 -->
      <div class="flex items-center gap-3 border-b border-bk-border px-5 py-5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-bk-yellow">
          <i class="fa-solid fa-chart-line text-white text-sm"></i>
        </div>
        <span class="font-bold tracking-tight text-bk-text">Invest<span class="text-bk-yellow">Flow</span></span>
      </div>

      <!-- 네비게이션 -->
      <nav class="flex-1 space-y-0.5 px-3 py-4">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all"
          :class="
            currentView === item.id
              ? 'bg-bk-yellow/10 text-bk-yellow font-semibold'
              : 'text-bk-text-2 hover:bg-bk-elevated hover:text-bk-text'
          "
          @click="currentView = item.id"
        >
          <i :class="[item.icon, 'w-4 text-center text-base flex-shrink-0',
             currentView === item.id ? 'text-bk-yellow' : 'text-bk-text-3']"></i>
          {{ item.label }}
        </button>
      </nav>

      <!-- 사용자 정보 + Footer -->
      <div class="border-t border-bk-border">
        <div class="flex items-center gap-2.5 px-4 py-3">
          <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-bk-yellow/10 text-bk-yellow text-sm font-bold">
            {{ user?.displayName?.charAt(0) ?? 'U' }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-bk-text">{{ user?.displayName }}</p>
            <button
              class="flex items-center gap-1 text-xs text-bk-text-3 hover:text-red-500 transition-colors"
              @click="logout"
            >
              <i class="fa-solid fa-right-from-bracket text-xs"></i> 로그아웃
            </button>
          </div>
        </div>
        <!-- Sidebar Footer -->
        <a href="https://www.edumgt.co.kr" target="_blank" rel="noopener"
           class="flex items-center justify-center gap-1.5 border-t border-bk-border px-4 py-2.5 hover:bg-bk-elevated transition-colors">
          <i class="fa-solid fa-building text-bk-text-3 text-xs"></i>
          <span class="text-xs text-bk-text-3 hover:text-bk-yellow transition-colors">(주)에듀엠지티</span>
        </a>
      </div>
    </aside>

    <!-- 콘텐츠 영역 -->
    <div class="flex flex-1 flex-col overflow-hidden">

      <!-- 모바일 상단바 -->
      <header class="flex items-center justify-between border-b border-bk-border bg-bk-surface px-4 py-3 md:hidden shadow-card">
        <div class="flex items-center gap-2">
          <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-bk-yellow">
            <i class="fa-solid fa-chart-line text-white text-xs"></i>
          </div>
          <span class="font-bold text-bk-text">Invest<span class="text-bk-yellow">Flow</span></span>
        </div>
        <button class="text-xs text-bk-text-3 hover:text-red-500 transition-colors" @click="logout">
          <i class="fa-solid fa-right-from-bracket"></i>
        </button>
      </header>

      <!-- 페이지 헤더 -->
      <div class="border-b border-bk-border bg-bk-surface px-6 py-4 flex items-center gap-3">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg"
             style="background: rgba(15,108,189,0.10);">
          <i :class="[navItems.find(n => n.id === currentView)?.icon ?? '', 'text-bk-yellow text-sm']"></i>
        </div>
        <h1 class="text-base font-bold text-bk-text">
          {{ navItems.find((n) => n.id === currentView)?.label }}
        </h1>
      </div>

      <!-- 메인 콘텐츠 -->
      <main class="flex-1 overflow-y-auto bg-bk-bg p-4 md:p-6">
        <Dashboard
          v-if="currentView === 'dashboard'"
          :investments="investments"
          :events="events"
          @goto="(v) => (currentView = v as typeof currentView)"
        />
        <CalendarView
          v-else-if="currentView === 'calendar'"
          :events="events"
          :api-url="apiUrl"
          :token="token"
          @event-added="fetchAll"
        />
        <AIRecommendations
          v-else-if="currentView === 'ai'"
          :api-url="apiUrl"
          :token="token"
          @event-added="fetchAll"
        />
        <PortfolioManager
          v-else-if="currentView === 'portfolio'"
          :investments="investments"
          :api-url="apiUrl"
          :token="token"
          @changed="fetchInvestments"
        />
        <ImageClassifier
          v-else-if="currentView === 'quality'"
          :api-url="apiUrl"
          :token="token"
        />
        <AirflowMonitor
          v-else-if="currentView === 'airflow'"
          :api-url="apiUrl"
          :token="token"
        />
      </main>

      <!-- Footer -->
      <footer class="border-t border-bk-border bg-bk-surface px-6 py-3 hidden md:flex items-center justify-between">
        <div class="flex items-center gap-3">
          <a href="https://www.edumgt.co.kr" target="_blank" rel="noopener"
             class="flex items-center gap-2 text-bk-text-3 hover:text-bk-yellow transition-colors">
            <i class="fa-solid fa-building text-xs"></i>
            <span class="text-xs font-semibold">(주)에듀엠지티</span>
          </a>
          <span class="text-bk-text-3 text-xs">·</span>
          <a href="https://www.edumgt.co.kr" target="_blank" rel="noopener"
             class="text-xs text-bk-text-3 hover:text-bk-yellow transition-colors">
            www.edumgt.co.kr
          </a>
        </div>
        <p class="text-xs text-bk-text-3">© 2025 EduMGT Co., Ltd.</p>
      </footer>

      <!-- 모바일 하단 탭바 -->
      <nav class="flex border-t border-bk-border bg-bk-surface md:hidden">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="flex flex-1 flex-col items-center gap-0.5 py-3 text-xs transition-colors"
          :class="currentView === item.id ? 'text-bk-yellow' : 'text-bk-text-3'"
          @click="currentView = item.id"
        >
          <i :class="[item.icon, 'text-lg']"></i>
          {{ item.label }}
        </button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import Dashboard from './components/Dashboard.vue';
import CalendarView from './components/CalendarView.vue';
import AIRecommendations from './components/AIRecommendations.vue';
import PortfolioManager from './components/PortfolioManager.vue';
import ImageClassifier from './components/ImageClassifier.vue';
import AirflowMonitor from './components/AirflowMonitor.vue';

type User = { id: number; username: string; displayName: string };
type Investment = {
  id: number; ticker: string; asset_name: string; asset_type: string;
  quantity: number; avg_price: number; currency: string;
};
type InvestmentEvent = {
  id: number; title: string; event_type: string; ticker: string;
  start: string; end: string; notes: string;
  is_ai_recommended: boolean; priority: string; status: string;
};

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const token = ref(localStorage.getItem('token') || '');
const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'));
const username = ref('test1');
const password = ref('123456');
const loginError = ref('');
const loginLoading = ref(false);

const currentView = ref<'dashboard' | 'calendar' | 'ai' | 'portfolio' | 'quality' | 'airflow'>('dashboard');
const investments = ref<Investment[]>([]);
const events = ref<InvestmentEvent[]>([]);

const navItems = [
  { id: 'dashboard', icon: 'fa-solid fa-gauge-high',     label: '대시보드' },
  { id: 'calendar',  icon: 'fa-solid fa-calendar-days',  label: '금융 캘린더' },
  { id: 'ai',        icon: 'fa-solid fa-robot',          label: 'AI 추천' },
  { id: 'portfolio', icon: 'fa-solid fa-briefcase',      label: '포트폴리오' },
  { id: 'quality',   icon: 'fa-solid fa-shield-halved',  label: '품질 검사' },
  { id: 'airflow',   icon: 'fa-solid fa-wind',           label: 'Airflow' },
] as const;

async function fetchInvestments() {
  const res = await fetch(`${apiUrl}/api/investments`, {
    headers: { Authorization: `Bearer ${token.value}` },
  });
  if (res.status === 401) { logout(); return; }
  investments.value = await res.json();
}

async function fetchEvents() {
  const res = await fetch(`${apiUrl}/api/calendar/events`, {
    headers: { Authorization: `Bearer ${token.value}` },
  });
  if (res.status === 401) { logout(); return; }
  events.value = await res.json();
}

async function fetchAll() {
  await Promise.all([fetchInvestments(), fetchEvents()]);
}

async function handleLogin() {
  loginError.value = '';
  loginLoading.value = true;
  try {
    const res = await fetch(`${apiUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    });
    if (!res.ok) throw new Error((await res.json()).message || '로그인 실패');
    const data = await res.json();
    token.value = data.token;
    user.value = data.user;
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    await fetchAll();
  } catch (err) {
    loginError.value = err instanceof Error ? err.message : '알 수 없는 오류';
  } finally {
    loginLoading.value = false;
  }
}

function logout() {
  token.value = '';
  user.value = null;
  investments.value = [];
  events.value = [];
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

onMounted(async () => {
  if (token.value) {
    try { await fetchAll(); }
    catch { logout(); }
  }
});
</script>
