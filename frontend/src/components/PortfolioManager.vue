<template>
  <div class="space-y-4">

    <!-- ── 요약 지표 ──────────────────────────────────────────────────── -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <div class="card-bk p-5">
        <p class="label-caps mb-2">KRW 평가액</p>
        <p class="font-mono text-xl font-bold text-bk-yellow">{{ krwValue }}</p>
      </div>
      <div class="card-bk p-5">
        <p class="label-caps mb-2">USD 평가액</p>
        <p class="font-mono text-xl font-bold text-bk-yellow">{{ usdValue }}</p>
      </div>
      <div class="col-span-2 card-bk p-5 sm:col-span-1">
        <p class="label-caps mb-2">보유 종목 수</p>
        <p class="font-mono text-2xl font-bold text-bk-text">{{ investments.length }}<span class="ml-1 text-base text-bk-text-2">종목</span></p>
      </div>
    </div>

    <!-- ── 종목 테이블 ────────────────────────────────────────────────── -->
    <div class="card-bk overflow-hidden">
      <div class="flex items-center justify-between border-b border-bk-border px-5 py-4 bg-bk-elevated">
        <p class="font-semibold text-bk-text">보유 종목</p>
        <button class="btn-yellow flex items-center gap-2 px-4 py-2 text-sm" @click="showAddModal = true">
          <i class="fa-solid fa-plus"></i> 종목 추가
        </button>
      </div>

      <div v-if="investments.length === 0" class="flex flex-col items-center justify-center py-16 text-bk-text-3">
        <div class="flex h-16 w-16 items-center justify-center rounded-full bg-bk-elevated">
          <i class="fa-solid fa-briefcase text-2xl"></i>
        </div>
        <p class="mt-4 text-sm font-medium text-bk-text-2">보유 종목이 없습니다</p>
        <p class="text-xs mt-1">위의 버튼으로 추가하세요</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[600px]">
          <thead>
            <tr class="border-b border-bk-border bg-bk-elevated">
              <th class="px-5 py-3 text-left label-caps">종목</th>
              <th class="px-3 py-3 text-center label-caps">유형</th>
              <th class="px-3 py-3 text-right label-caps">수량</th>
              <th class="px-3 py-3 text-right label-caps">평균단가</th>
              <th class="px-5 py-3 text-right label-caps">평가액</th>
              <th class="px-3 py-3"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="inv in investments"
              :key="inv.id"
              class="border-b border-bk-border last:border-0 hover:bg-bk-elevated transition-colors"
            >
              <td class="px-5 py-3">
                <div class="flex items-center gap-2.5">
                  <i :class="[assetIcon(inv.asset_type), 'text-bk-text-3 w-4 text-center']"></i>
                  <div>
                    <p class="font-medium text-bk-text">{{ inv.asset_name }}</p>
                    <p class="font-mono text-xs text-bk-yellow font-semibold">{{ inv.ticker }}</p>
                  </div>
                </div>
              </td>
              <td class="px-3 py-3 text-center">
                <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="assetClass(inv.asset_type)">
                  {{ assetKo(inv.asset_type) }}
                </span>
              </td>
              <td class="px-3 py-3 text-right font-mono text-sm text-bk-text">
                {{ inv.quantity.toLocaleString() }}
              </td>
              <td class="px-3 py-3 text-right font-mono text-sm text-bk-text-2">
                {{ inv.avg_price.toLocaleString() }}
                <span class="ml-0.5 text-xs text-bk-text-3">{{ inv.currency }}</span>
              </td>
              <td class="px-5 py-3 text-right">
                <p class="font-mono text-sm font-bold text-bk-text">{{ totalVal(inv) }}</p>
              </td>
              <td class="px-3 py-3 text-center">
                <button
                  class="text-bk-text-3 hover:text-red-500 transition-colors p-1 rounded hover:bg-red-50"
                  @click="remove(inv.id)"
                >
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 종목 추가 모달 ─────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div class="w-full max-w-md rounded-xl border border-bk-border bg-white shadow-modal">

          <div class="flex items-center justify-between border-b border-bk-border px-6 py-4 bg-bk-elevated rounded-t-xl">
            <p class="font-semibold text-bk-text">종목 추가</p>
            <button class="rounded-md p-1 text-bk-text-3 hover:bg-bk-border hover:text-bk-text transition-colors" @click="showAddModal = false">
              <i class="fa-solid fa-xmark text-base"></i>
            </button>
          </div>

          <form class="space-y-4 px-6 py-5" @submit.prevent="submitAdd">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label-caps mb-2 block">티커 *</label>
                <input v-model="form.ticker" class="input-bk font-mono" placeholder="005930" required />
              </div>
              <div>
                <label class="label-caps mb-2 block">자산 유형</label>
                <select v-model="form.asset_type" class="input-bk">
                  <option value="stock">주식</option>
                  <option value="etf">ETF</option>
                  <option value="bond">채권</option>
                  <option value="crypto">암호화폐</option>
                  <option value="reit">리츠</option>
                </select>
              </div>
            </div>

            <div>
              <label class="label-caps mb-2 block">종목명 *</label>
              <input v-model="form.asset_name" class="input-bk" placeholder="삼성전자" required />
            </div>

            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="label-caps mb-2 block">수량 *</label>
                <input v-model.number="form.quantity" type="number" step="0.0001" min="0"
                  class="input-bk font-mono" required />
              </div>
              <div>
                <label class="label-caps mb-2 block">평균단가 *</label>
                <input v-model.number="form.avg_price" type="number" step="0.01" min="0"
                  class="input-bk font-mono" required />
              </div>
              <div>
                <label class="label-caps mb-2 block">통화</label>
                <select v-model="form.currency" class="input-bk">
                  <option value="KRW">KRW</option>
                  <option value="USD">USD</option>
                </select>
              </div>
            </div>

            <p v-if="formError" class="flex items-center gap-1.5 text-sm text-red-500">
              <i class="fa-solid fa-circle-exclamation"></i>{{ formError }}
            </p>

            <div class="flex gap-3 border-t border-bk-border pt-4">
              <button type="button" class="btn-ghost flex-1 py-2.5 text-sm" @click="showAddModal = false">
                취소
              </button>
              <button type="submit" :disabled="submitting"
                class="btn-yellow flex-1 flex items-center justify-center gap-2 py-2.5 text-sm">
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
import { computed, reactive, ref } from 'vue';

type Investment = {
  id: number; ticker: string; asset_name: string; asset_type: string;
  quantity: number; avg_price: number; currency: string;
};

const props = defineProps<{ investments: Investment[]; apiUrl: string; token: string }>();
const emit = defineEmits<{ (e: 'changed'): void }>();

const showAddModal = ref(false);
const submitting = ref(false);
const formError = ref('');
const form = reactive({
  ticker: '', asset_name: '', asset_type: 'stock',
  quantity: 0, avg_price: 0, currency: 'KRW',
});

const krwValue = computed(() => {
  const v = props.investments.filter(i => i.currency === 'KRW').reduce((s, i) => s + i.quantity * i.avg_price, 0);
  return v >= 100_000_000 ? (v / 100_000_000).toFixed(2) + '억원'
       : v >= 10_000_000  ? (v / 10_000_000).toFixed(1) + '천만원'
       : v.toLocaleString() + '원';
});

const usdValue = computed(() => {
  const v = props.investments.filter(i => i.currency === 'USD').reduce((s, i) => s + i.quantity * i.avg_price, 0);
  return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 0 });
});

function totalVal(inv: Investment) {
  const v = inv.quantity * inv.avg_price;
  return inv.currency === 'USD'
    ? '$' + v.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : v.toLocaleString() + '원';
}

function assetIcon(t: string) {
  return ({ stock:'fa-solid fa-chart-line', etf:'fa-solid fa-layer-group',
            bond:'fa-solid fa-file-contract', crypto:'fa-brands fa-bitcoin',
            reit:'fa-solid fa-building' } as Record<string,string>)[t] ?? 'fa-solid fa-circle-dot';
}

function assetKo(t: string) {
  return ({ stock:'주식', etf:'ETF', bond:'채권', crypto:'코인', reit:'리츠' } as Record<string,string>)[t] ?? t;
}

function assetClass(t: string) {
  return ({
    stock: 'bg-green-50 text-green-700 border border-green-200',
    etf:   'bg-blue-50 text-blue-700 border border-blue-200',
    bond:  'bg-amber-50 text-amber-700 border border-amber-200',
    crypto:'bg-orange-50 text-orange-700 border border-orange-200',
    reit:  'bg-purple-50 text-purple-700 border border-purple-200',
  } as Record<string,string>)[t] ?? 'bg-bk-elevated text-bk-text-2';
}

async function submitAdd() {
  formError.value = '';
  submitting.value = true;
  try {
    const res = await fetch(`${props.apiUrl}/api/investments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${props.token}` },
      body: JSON.stringify(form),
    });
    if (!res.ok) throw new Error((await res.json()).message);
    showAddModal.value = false;
    Object.assign(form, { ticker:'', asset_name:'', asset_type:'stock', quantity:0, avg_price:0, currency:'KRW' });
    emit('changed');
  } catch (err) {
    formError.value = err instanceof Error ? err.message : '저장 실패';
  } finally {
    submitting.value = false;
  }
}

async function remove(id: number) {
  if (!confirm('이 종목을 삭제하시겠습니까?')) return;
  const res = await fetch(`${props.apiUrl}/api/investments/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${props.token}` },
  });
  if (res.ok) emit('changed');
}
</script>
