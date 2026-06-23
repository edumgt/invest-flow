# InvestFlow
 
> **AI 기반 개인 투자 일정 관리 웹앱** — Vue 3 · Node.js · PostgreSQL · Claude AI

[![Vue 3](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js)](https://vuejs.org)
[![Node.js](https://img.shields.io/badge/Node.js-20-green?style=flat-square&logo=node.js)](https://nodejs.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed?style=flat-square&logo=docker)](docker-compose.yml)
[![Claude AI](https://img.shields.io/badge/Claude-AI-orange?style=flat-square)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**InvestFlow**는 개인 투자자를 위한 AI 비서 웹앱입니다.  
보유 포트폴리오를 관리하고, AI(Claude)가 분석하여 매수·매도·리밸런싱 일정을 자동으로 제안합니다.  
제안된 일정은 컬러 코드 투자 캘린더에 바로 등록할 수 있습니다.

---

![alt text](image.png)

![alt text](image-1.png)

![alt text](image-2.png)

![alt text](image-3.png)


---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **대시보드** | 포트폴리오 요약, 다가오는 투자 일정, AI 추천 바로가기 |
| **투자 캘린더** | 매수·매도·배당·실적발표·리밸런싱을 컬러별로 구분 표시 |
| **AI 추천** | Claude AI가 포트폴리오 분석 후 5개 투자 액션 일정 제안 |
| **포트폴리오 관리** | 보유 종목(주식·ETF·채권·암호화폐·리츠) CRUD |

## 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | Vue 3 + Vite + TypeScript + Tailwind CSS + TUI Calendar |
| Backend | Node.js (ESM, no framework) + JWT (HMAC-SHA256) |
| Database | PostgreSQL 16 + pgcrypto |
| AI | Anthropic Claude API (claude-sonnet-4-6) |
| DevOps | Docker Compose + GitLab CI + Apache Airflow |

---

## 빠른 시작 (Docker)

```bash
cp .env.example .env
# .env 에서 ANTHROPIC_API_KEY 입력 (선택 — 없으면 목 데이터로 동작)

docker compose up --build -d
```

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:3000/health

DB 초기화 후 재시작:

```bash
docker compose down -v
docker compose up --build -d
```

---

## 로컬 개발 (비도커)

### 1) Frontend

```bash
npm install
npm run dev
```

### 2) Backend

```bash
cd backend
cp ../.env.example .env
npm install
npm run dev
```

---

## 테스트 계정

| 계정 | 비밀번호 | 포트폴리오 |
|------|----------|-----------|
| `alice` | `Passw0rd!` | 삼성전자·SK하이닉스·TIGER S&P500·AAPL·KODEX200 |
| `bob`   | `Passw0rd!` | NVIDIA·나스닥100 ETF·BTC |
| `carol` | `Passw0rd!` | (비어있음 — 직접 추가 테스트용) |

---

## AI 추천 흐름

```
사용자 → [AI 추천] 탭 → "AI 분석 시작" 클릭
     → POST /api/ai/recommend
     → 백엔드: DB에서 포트폴리오 조회
     → Claude API 호출 (ANTHROPIC_API_KEY 미설정 시 목 데이터)
     → 5개 투자 액션 + 추천 날짜 반환
     → 사용자: 개별 or 전체 "캘린더에 추가"
     → 투자 캘린더에 AI 추천 이벤트 등록
```

---

## API 엔드포인트

| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/auth/login` | JWT 로그인 |
| GET | `/api/investments` | 포트폴리오 조회 |
| POST | `/api/investments` | 종목 추가 |
| DELETE | `/api/investments/:id` | 종목 삭제 |
| GET | `/api/calendar/events` | 투자 이벤트 목록 |
| POST | `/api/calendar/events` | 이벤트 추가 |
| DELETE | `/api/calendar/events/:id` | 이벤트 삭제 |
| POST | `/api/ai/recommend` | AI 투자 일정 추천 |

---

## 이벤트 유형 & 컬러

| 유형 | 컬러 | 의미 |
|------|------|------|
| 매수 | 초록 | 주식/ETF 매수 예정 |
| 매도 | 빨강 | 매도·수익실현 예정 |
| 배당 | 파랑 | 배당금 수령일 |
| 실적발표 | 주황 | 어닝 시즌 모니터링 |
| 리밸런싱 | 보라 | 포트폴리오 리밸런싱 |
| 모니터링 | 청록 | 목표가·조건 모니터링 |
| 일반 | 회색 | 기타 투자 메모 |

---

## DevOps (선택)

- **GitLab CI**: `.gitlab-ci.yml` — 빌드·테스트·배포 파이프라인
- **Airflow**: `docker-compose.airflow.yml` — 정기 파이프라인 트리거
- **이중 Push**: `scripts/setup-dual-remote.sh` — GitHub ↔ GitLab 동기화


