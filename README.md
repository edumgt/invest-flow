# calflow

> **Full-stack calendar SPA with JWT auth, Docker DevOps, and Airflow orchestration**

[![GitHub Sponsors](https://img.shields.io/github/sponsors/edumgt?style=flat-square&logo=github&label=Sponsor)](https://github.com/sponsors/edumgt)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Vue 3](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js)](https://vuejs.org)
[![Node.js](https://img.shields.io/badge/Node.js-20-green?style=flat-square&logo=node.js)](https://nodejs.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed?style=flat-square&logo=docker)](docker-compose.yml)
[![Airflow](https://img.shields.io/badge/Airflow-2.10-017cee?style=flat-square&logo=apache-airflow)](docker-compose.airflow.yml)

**calflow** is a production-ready template that bundles a Vue 3 / TUI Calendar SPA, a Node.js REST backend, PostgreSQL, and a complete DevOps pipeline — GitLab CE, GitLab Runner, GitHub ↔ GitLab dual-push, and Apache Airflow pipeline orchestration — all wired together with Docker Compose.

---

## 💡 Why "calflow"?

| Component | Meaning |
|-----------|---------|
| **cal** | Calendar — the core feature of the application |
| **flow** | Workflow / Airflow — the DevOps orchestration layer that controls the pipeline |

The name is short (7 characters), memorable, and reflects both the **product** (a calendar app) and the **process** (automated workflow execution). It works equally well as a package name, a domain (`calflow.dev`), and a project brand.

### Recommended repository names (ranked)

| # | Name | Rationale |
|---|------|-----------|
| ⭐ 1 | **`calflow`** | Short, product + process, Airflow reference, globally unique, sponsor-friendly |
| 2 | **`planflow`** | "Plan" broadens the use-case beyond calendars; still references workflow |
| 3 | **`calstack`** | Emphasises the full-stack nature; easy to type |
| 4 | **`vue-calflow`** | Explicit Vue branding for discoverability in Vue ecosystems |
| 5 | **`calops`** | Calendar + DevOps; appeals to DevOps-focused audiences |

---

## ✨ Features

- JWT login authentication (JWT 로그인 인증)
- Per-user calendar event management (사용자별 캘린더 일정 조회)
- Offcanvas SPA UI (Offcanvas 메뉴 기반 SPA UI)
- PostgreSQL auto-seeded with 3 test accounts (초기 SQL 삽입)
- WSL2 / Windows dev support (WSL 환경 개발 지원)
- GitLab CE + GitLab Runner via Docker (GitLab CE + GitLab Runner Docker 구성)
- GitHub ↔ GitLab dual-push (GitHub ↔ GitLab 이중 push 지원)
- Apache Airflow pipeline orchestration (Airflow 기반 파이프라인 오케스트레이션)

## 🏗️ Stack

- `frontend`  : Vue 3 + Vite + Tailwind CSS + TUI Calendar
- `backend`   : Node.js HTTP server + PostgreSQL + JWT (HMAC-SHA256)
- `postgres`  : PostgreSQL 16
- `gitlab`    : GitLab CE 17 (Docker)
- `runner`    : GitLab Runner (Docker executor)
- `airflow`   : Apache Airflow 2.10 (CeleryExecutor)

---

## 💖 Sponsor this project

If **calflow** saves you time, please consider sponsoring the project. Your support keeps the template up-to-date with the latest Vue, Node.js, and Airflow releases and motivates adding new features such as multi-tenant support, event notifications, and a mobile-optimised view.

[![Sponsor via GitHub](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/edumgt)

---

## 🚀 Quick start (Docker — app server)

```bash
docker compose up --build -d
```

서비스 접속:

- Frontend: http://localhost:5173
- Backend health: http://localhost:3000/health

종료:

```bash
docker compose down
```

DB를 초기화하고 다시 시작:

```bash
docker compose down -v
docker compose up --build -d
```

---

## GitLab CE 설정

### 1. GitLab + Runner 컨테이너 시작

```bash
docker compose -f docker-compose.gitlab.yml up -d
```

> GitLab 초기 기동은 약 3~5분이 소요됩니다.

- GitLab UI: http://localhost:8080
- SSH 포트: 2222

### 2. 초기 root 비밀번호 확인

```bash
docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

### 3. GitLab Runner 등록

GitLab UI 접속 후 **Admin > CI/CD > Runners > New instance runner** 에서 등록 토큰 발급 후:

```bash
chmod +x scripts/register-gitlab-runner.sh
./scripts/register-gitlab-runner.sh --token glrt-<YOUR_TOKEN>
```

---

## GitHub + GitLab 이중 Push 설정

### 방법 1: 스크립트 사용 (권장)

```bash
chmod +x scripts/setup-dual-remote.sh
./scripts/setup-dual-remote.sh \
    --gitlab-url http://localhost:8080 \
    --gitlab-project <namespace>/<project-name>
```

설정 후 `git push origin main` 한 번으로 GitHub와 GitLab 모두에 push됩니다.

### 방법 2: GitHub Actions 자동 미러링

`main` 브랜치 push 시 GitHub Actions가 GitLab으로 자동 미러링합니다.
GitHub 저장소 **Settings > Secrets and variables > Actions** 에 아래 시크릿을 등록하세요:

| 시크릿 이름            | 값 예시                                           |
|------------------------|---------------------------------------------------|
| `GITLAB_URL`           | `http://gitlab.local:8080`                        |
| `GITLAB_TOKEN`         | GitLab Personal Access Token (api scope)          |
| `GITLAB_PROJECT_PATH`  | `edumgt/Vue_vite_tailwind_tui.calendar`           |

---

## Airflow 설정 (GitLab 파이프라인 오케스트레이션)

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 파일에서 GITLAB_TOKEN, GITLAB_PROJECT_ID 등 입력
```

### 2. Airflow 초기화 및 시작

```bash
# Linux: UID 확인 후 설정
echo "AIRFLOW_UID=$(id -u)" >> .env

# DB 초기화 (최초 1회)
docker compose -f docker-compose.airflow.yml up airflow-init

# 서비스 시작
docker compose -f docker-compose.airflow.yml up -d
```

- Airflow UI: http://localhost:8793
- 기본 계정: admin / admin

### 3. DAG 구성

`airflow/dags/calendar_pipeline_dag.py` DAG가 자동으로 로드됩니다.

Airflow UI에서 아래 Variable을 등록하세요 (**Admin > Variables**):

| Key                  | 값                                              |
|----------------------|--------------------------------------------------|
| `GITLAB_URL`         | `http://gitlab.local:8080`                       |
| `GITLAB_TOKEN`       | GitLab Personal Access Token                     |
| `GITLAB_PROJECT_ID`  | GitLab 프로젝트 ID 또는 경로                      |

### 4. 파이프라인 수동 트리거

Airflow UI에서 `calendar_app_pipeline` DAG를 찾아 **Trigger DAG w/ config** 버튼을 클릭:

```json
{
  "branch": "main",
  "variables": {
    "DEPLOY_ENV": "staging"
  }
}
```

---

## 전체 아키텍처

```
[개발자]
   │
   ├── git push origin main
   │      │
   │      ├──▶ GitHub (origin)
   │      │        │
   │      │        └── GitHub Actions ──▶ GitLab 미러링 (mirror-to-gitlab job)
   │      │
   │      └──▶ GitLab (pushurl 설정 시 동시 push)
   │               │
   │               └── GitLab Runner ──▶ .gitlab-ci.yml 실행
   │                        │
   │                        └── Airflow 콜백 (notify:airflow job)
   │
   └── Airflow Scheduler (매일 17:00 UTC)
            │
            └── calendar_app_pipeline DAG
                     ├── trigger_pipeline  → GitLab API 파이프라인 트리거
                     ├── monitor_pipeline  → 완료까지 폴링
                     ├── fetch_jobs        → 잡 결과 수집
                     └── report_result     → 결과 보고
```

---

## 테스트 계정 (초기 SQL 삽입)

아래 계정은 `backend/sql/init.sql` 에서 자동 생성됩니다.

- `alice / Passw0rd!`
- `bob / Passw0rd!`
- `carol / Passw0rd!`

삽입 SQL:

```sql
INSERT INTO users (username, display_name, password_hash)
VALUES
  ('alice', 'Alice Kim', crypt('Passw0rd!', gen_salt('bf'))),
  ('bob', 'Bob Lee', crypt('Passw0rd!', gen_salt('bf'))),
  ('carol', 'Carol Park', crypt('Passw0rd!', gen_salt('bf')))
ON CONFLICT (username) DO NOTHING;
```

> pgcrypto의 `crypt` + `gen_salt('bf')`를 사용해 bcrypt 해시로 저장됩니다.

## WSL 개발 가이드

1. WSL2(Ubuntu)에서 프로젝트를 열고 Docker Desktop의 WSL 통합을 활성화합니다.
2. 아래 명령으로 실행합니다.

```bash
docker compose up --build
```

3. VS Code Remote - WSL 환경에서 수정하면 hot-reload로 즉시 반영됩니다.

## 로컬(비도커) 실행

### 1) frontend

```bash
npm install
npm run dev -- --host
```

### 2) backend

```bash
cd backend
cp .env.example .env
npm run dev
```

PostgreSQL은 별도로 실행한 뒤 `DATABASE_URL`을 맞춰주세요.

## 로그인 API 테스트 예시

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Passw0rd!"}'
```

토큰으로 일정 조회:

```bash
curl http://localhost:3000/api/calendar/events \
  -H "Authorization: Bearer <JWT_TOKEN>"
```
