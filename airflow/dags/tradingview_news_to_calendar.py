"""
tradingview_news_to_calendar.py
================================
TradingView 한국 블로그(https://www.tradingview.com/blog/ko/)에서
5분마다 최신 뉴스를 수집하여 InvestFlow 캘린더에 이벤트로 추가합니다.

중복 방지: 기사 URL의 포스트 ID를 이벤트 제목에 포함시켜 판단합니다.
"""

# Python 3.10 미만에서도 타입 힌트(list[dict] 등 소문자 형식)를 쓸 수 있게 해주는 임포트
from __future__ import annotations

import logging          # Airflow 로그 출력용 (print 대신 사용)
import os               # 환경 변수(BACKEND_URL 등)를 읽기 위한 모듈
import re               # HTML에서 패턴을 추출하는 정규 표현식 모듈
from datetime import datetime, timedelta, timezone  # 날짜/시간 처리

import requests                                    # HTTP 요청 (스크래핑, 백엔드 API 호출)
from airflow import DAG                            # DAG(워크플로우) 정의 클래스
from airflow.operators.python import PythonOperator  # Python 함수를 태스크로 실행하는 오퍼레이터


# ── 모듈 단위 로거 설정 ──────────────────────────────────────────────────────
# __name__ = 'tradingview_news_to_calendar' → Airflow UI 로그에서 파일명으로 구분 가능
log = logging.getLogger(__name__)


# ── 전역 상수 ────────────────────────────────────────────────────────────────

# 스크래핑 대상 TradingView 한국 블로그 URL
BLOG_URL    = "https://www.tradingview.com/blog/ko/"

# InvestFlow 백엔드 API 주소
# - 환경 변수 BACKEND_URL이 있으면 그 값을 사용, 없으면 기본값(Windows PC VMnet8 IP)
# - 192.168.253.1 : VMware Host-Only/NAT 어댑터(Windows PC)의 IP
# - 8301 : Windows portproxy → WSL2 Docker backend:3000 으로 포워딩된 포트
BACKEND_URL = os.environ.get("BACKEND_URL", "http://192.168.253.1:8301")

# 백엔드 로그인에 사용할 계정 (환경 변수 우선, 없으면 기본값)
TV_USER = os.environ.get("BACKEND_USER", "test1")
TV_PASS = os.environ.get("BACKEND_PASS", "123456")

# 한국 표준시 (UTC+9) 타임존 객체
KST = timezone(timedelta(hours=9))

# TradingView 스크래핑 시 전송할 HTTP 헤더
# - User-Agent : 브라우저처럼 위장해 차단(403) 방지
# - Accept-Language : 한국어 블로그 콘텐츠를 받기 위한 언어 설정
# - Accept : HTML 문서를 요청한다고 명시
SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 영문 월 약어 → 숫자 변환 딕셔너리
# TradingView 날짜가 'Jun 16' 형식으로 표시되기 때문에 필요
MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


# ── 파싱 헬퍼 함수 ───────────────────────────────────────────────────────────

def _strip_tags(text: str) -> str:
    # HTML 태그(<...>)를 모두 제거하고 앞뒤 공백을 정리해 순수 텍스트만 반환
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_date(date_str: str) -> datetime:
    """'Jun 16' 형식 → KST datetime. 연도는 현재 연도 사용."""
    # 'Jun 16' 패턴에서 월 약어(\w{3})와 일(\d{1,2})을 추출
    m = re.match(r"(\w{3})\s+(\d{1,2})", date_str.strip())
    if not m:
        # 패턴이 맞지 않으면 현재 시각을 KST로 반환 (안전 처리)
        return datetime.now(KST)
    # 월 약어(예: 'Jun')를 숫자(6)로 변환, 매핑 실패 시 이번 달 사용
    month = MONTH_MAP.get(m.group(1), datetime.now().month)
    day   = int(m.group(2))          # 일(day) 정수 변환
    year  = datetime.now().year      # 연도는 항상 현재 연도로 고정
    # 오전 9시 KST로 datetime 객체 생성 (블로그 발행 시간 기준)
    return datetime(year, month, day, 9, 0, tzinfo=KST)


def _parse_articles(html: str) -> list[dict]:
    """
    <article ... class="... post-XXXXX ..."> 블록을 분리해 파싱합니다.
    각 블록에서 URL / 제목 / 날짜 / 카테고리를 추출합니다.
    """
    articles = []

    # '<article ' 태그를 기준으로 HTML을 분리 → 각 원소가 하나의 기사 블록
    # [1:] 로 split() 첫 번째 요소(article 태그 이전 헤더 영역)를 버림
    blocks = re.split(r"<article\s+", html)[1:]

    for block in blocks:
        # ── 포스트 ID 추출 ──
        # id="post-58839" 또는 class="... post-58839 ..." 두 형식 모두 처리
        # \d{4,} : 4자리 이상 숫자만 매칭해 CSS 클래스 숫자와 혼동 방지
        pid_m = re.search(r"post-(\d{4,})", block)
        if not pid_m:
            # 포스트 ID가 없는 블록(광고, 배너 등)은 건너뜀
            continue
        post_id = int(pid_m.group(1))  # 문자열 → 정수 변환 (중복 비교 시 int 사용)

        # ── 기사 URL 추출 ──
        # TradingView 블로그 URL 패턴: /blog/ko/슬러그-포스트ID/
        # 슬러그는 소문자 알파벳·숫자·하이픈만 허용, 끝에 4자리 이상 숫자(포스트ID)
        url_m = re.search(
            r'href="(https://www\.tradingview\.com/blog/ko/[a-z0-9\-]+-\d{4,}/)"',
            block,
        )
        if not url_m:
            # 블로그 URL이 없는 블록은 건너뜀 (사이드바, 관련 링크 등)
            continue

        # ── 기사 제목 추출 ──
        # 특집 기사: <h2 class="title">제목</h2>
        # 일반 기사: <h3 class="title">제목</h3>
        # [^>]* : class 속성 외 다른 속성(id, data-* 등)이 있어도 매칭
        # [\s\S]+? : 제목 안에 줄바꿈이 있어도 모두 캡처 (최소 매칭)
        title_m = re.search(r'<h[23][^>]*class="title"[^>]*>([\s\S]+?)</h[23]>', block)
        # 제목 내부에 <span>, <em> 등 태그가 있을 수 있어 _strip_tags로 제거
        title = _strip_tags(title_m.group(1)).strip() if title_m else ""

        # ── 발행일 추출 ──
        # HTML 패턴: <div class="date">Jun 16</div>
        date_m = re.search(r'class="date"[^>]*>([^<]+)</div>', block)
        # 매칭 성공 시 문자열 파싱, 실패 시 현재 시각(KST) 사용
        pub_dt = _parse_date(date_m.group(1)) if date_m else datetime.now(KST)

        # ── 카테고리 추출 ──
        # HTML 패턴: <a class="tv-category-link">시장분석</a>
        cat_m = re.search(r'class="tv-category-link">([^<]+)</a>', block)
        category = cat_m.group(1).strip() if cat_m else "뉴스"  # 없으면 기본값 '뉴스'

        # 제목을 추출하지 못한 블록은 저장하지 않음
        if not title:
            continue

        articles.append({
            "post_id":  post_id,           # 중복 체크 기준 ID
            "url":      url_m.group(1),    # 원본 기사 링크
            "title":    title[:200],       # 200자 초과 시 잘라냄 (DB 컬럼 제한)
            "pub_dt":   pub_dt,            # 발행일 datetime 객체
            "category": category,          # 카테고리 레이블 (예: '시장분석')
        })

    # 포스트 ID 내림차순 정렬 → 최신 기사가 먼저 처리됨
    articles.sort(key=lambda x: x["post_id"], reverse=True)
    return articles


# ── Task 함수 ────────────────────────────────────────────────────────────────

def scrape_news(**context) -> list[dict]:
    """TradingView 블로그 스크래핑"""
    # SCRAPE_HEADERS로 봇 차단 우회, timeout=20초 (네트워크 지연 고려)
    resp = requests.get(BLOG_URL, headers=SCRAPE_HEADERS, timeout=20)
    # 4xx/5xx 응답이면 예외를 발생시켜 Airflow가 태스크 실패로 처리하게 함
    resp.raise_for_status()

    # 응답 HTML을 파싱해 기사 목록(dict 리스트) 반환
    articles = _parse_articles(resp.text)
    log.info("스크래핑 완료: %d개 기사", len(articles))
    # 상위 5개 기사 요약을 로그에 출력 (Airflow UI에서 확인 가능)
    for a in articles[:5]:
        log.info("  [%d] %s (%s)", a["post_id"], a["title"][:60], a["category"])

    # datetime 객체는 JSON 직렬화 불가 → isoformat() 문자열로 변환 후 XCom에 저장
    # XCom : Airflow 태스크 간 데이터를 전달하는 내부 저장소
    serializable = [
        {**a, "pub_dt": a["pub_dt"].isoformat()}  # 나머지 필드는 그대로 복사
        for a in articles
    ]
    # key='articles' 로 저장 → add_to_calendar 태스크에서 같은 key로 꺼냄
    context["ti"].xcom_push(key="articles", value=serializable)
    return serializable  # Airflow가 반환값도 자동으로 XCom에 저장 (return_value key)


def add_to_calendar(**context) -> None:
    """스크래핑된 뉴스를 캘린더 이벤트로 추가 (중복 제외)"""
    # scrape_news 태스크가 XCom에 저장한 기사 목록을 꺼냄
    # task_ids='scrape_news' : 어느 태스크의 XCom을 읽을지 지정
    # or [] : scrape_news 결과가 None이면 빈 리스트로 대체
    articles = context["ti"].xcom_pull(key="articles", task_ids="scrape_news") or []
    if not articles:
        # 기사가 없으면 경고 로그만 남기고 정상 종료 (오류가 아님)
        log.warning("추가할 기사 없음")
        return

    # ── 백엔드 로그인 → JWT 토큰 발급 ──
    login = requests.post(
        f"{BACKEND_URL}/api/auth/login",          # 로그인 엔드포인트
        json={"username": TV_USER, "password": TV_PASS},  # 자격증명
        timeout=10,                               # 10초 내 응답 없으면 예외
    )
    login.raise_for_status()                      # 로그인 실패(401 등) 시 예외 발생
    token = login.json()["token"]                 # 응답 JSON에서 JWT 토큰 추출

    # 이후 모든 API 요청에 사용할 인증 헤더 딕셔너리
    auth  = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ── 기존 캘린더 이벤트 조회 → 중복 ID 수집 ──
    existing_resp = requests.get(f"{BACKEND_URL}/api/calendar/events", headers=auth, timeout=10)
    existing_ids: set[int] = set()  # 이미 등록된 TV 포스트 ID 집합
    if existing_resp.ok:
        for ev in existing_resp.json():
            # 이벤트 제목에서 '[TV-12345]' 패턴을 찾아 포스트 ID 추출
            m = re.search(r"\[TV-(\d+)\]", ev.get("title", ""))
            if m:
                existing_ids.add(int(m.group(1)))  # 집합에 추가 (자동 중복 제거)
    log.info("기존 TV 이벤트 ID: %s", sorted(existing_ids))

    # ── 신규 기사만 순서대로 캘린더에 등록 ──
    added = 0  # 이번 실행에서 새로 추가된 이벤트 수 카운터
    for article in articles:
        # 이미 등록된 포스트 ID면 건너뜀 (중복 방지)
        if article["post_id"] in existing_ids:
            log.info("이미 존재 [%d]: %s", article["post_id"], article["title"][:40])
            continue

        # XCom에서 꺼낸 pub_dt는 isoformat 문자열 → 다시 datetime 객체로 복원
        try:
            pub_dt = datetime.fromisoformat(article["pub_dt"])
        except Exception:
            # 파싱 실패 시 현재 시각(KST) 사용 (방어 처리)
            pub_dt = datetime.now(KST)

        # tzinfo가 없는 naive datetime이면 KST로 강제 지정
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=KST)

        # 이벤트 제목: '[TV-포스트ID] 기사제목' 형식으로 중복 식별자를 앞에 붙임
        title = f"[TV-{article['post_id']}] {article['title']}"
        start = pub_dt.isoformat()                          # 이벤트 시작 시각 (ISO 8601)
        end   = (pub_dt + timedelta(hours=1)).isoformat()  # 이벤트 종료 = 시작 + 1시간
        # notes 필드에 카테고리와 원본 URL을 함께 저장
        notes = f"{article['category']} | {article['url']}"

        # 백엔드 API가 요구하는 이벤트 생성 페이로드
        payload = {
            "title":             title[:200],    # 200자 초과 시 잘라냄
            "event_type":        "general",      # 일반 일정 유형
            "ticker":            None,           # 종목 코드 없음 (뉴스 이벤트)
            "start":             start,          # 시작 시각 (ISO 8601 문자열)
            "end":               end,            # 종료 시각 (ISO 8601 문자열)
            "notes":             notes,          # 카테고리 | URL
            "is_ai_recommended": False,          # AI 추천 이벤트가 아님
            "priority":          "LOW",          # 우선순위: 낮음 (뉴스는 참고용)
        }

        # POST /api/calendar/events 로 이벤트 생성 요청
        resp = requests.post(
            f"{BACKEND_URL}/api/calendar/events",
            json=payload,
            headers=auth,
            timeout=10,
        )
        if resp.ok:
            # 201 Created 등 성공 응답 → 카운터 증가 및 성공 로그
            log.info("✅ 추가 [%d]: %s", article["post_id"], article["title"][:50])
            added += 1
        else:
            # 400/500 등 실패 응답 → 경고 로그만 남기고 다음 기사 계속 처리
            log.warning("❌ 실패 (%d) [%d]: %s", resp.status_code, article["post_id"], resp.text[:100])

    # 이번 실행 요약 로그
    log.info("완료: %d개 신규 이벤트 추가", added)


# ── DAG 정의 ─────────────────────────────────────────────────────────────────

# 모든 태스크에 공통 적용되는 기본 인수
default_args: dict = {
    "owner":            "airflow",   # DAG 소유자 표시 (Airflow UI에 노출)
    "depends_on_past":  False,       # 이전 실행 성공 여부와 무관하게 독립 실행
    "email_on_failure": False,       # 실패 시 이메일 알림 비활성화
    "email_on_retry":   False,       # 재시도 시 이메일 알림 비활성화
    "retries":          1,           # 실패 시 1회 자동 재시도
    "retry_delay":      timedelta(minutes=2),  # 재시도 전 2분 대기
}

with DAG(
    dag_id="tradingview_news_to_calendar",  # Airflow UI에서 DAG를 식별하는 고유 ID
    default_args=default_args,              # 위에서 정의한 공통 인수 적용
    description="TradingView KO 블로그 뉴스 → InvestFlow 캘린더 자동 추가 (5분 주기)",
    schedule_interval="*/5 * * * *",       # cron 표현식: 매 5분마다 실행
    start_date=datetime(2026, 1, 1),       # DAG 활성화 기준 시작일 (과거 날짜)
    catchup=False,                         # 과거 미실행 구간을 소급 실행하지 않음
    max_active_runs=1,                     # 동시에 실행 중인 DAG 인스턴스를 1개로 제한 (중복 방지)
    tags=["news", "tradingview", "calendar", "scraping"],  # Airflow UI 필터링용 태그
) as dag:

    # ── Task 1: TradingView 블로그 스크래핑 ──
    # python_callable로 지정한 함수가 Worker에서 실행됨
    t_scrape = PythonOperator(
        task_id="scrape_news",          # 태스크 고유 ID (XCom pull 시 참조)
        python_callable=scrape_news,    # 실행할 Python 함수
    )

    # ── Task 2: 스크래핑 결과를 캘린더에 등록 ──
    t_add = PythonOperator(
        task_id="add_to_calendar",
        python_callable=add_to_calendar,
    )

    # ── 태스크 의존성 설정 ──
    # >> 연산자: t_scrape 가 성공해야 t_add 가 실행됨 (순차 실행)
    t_scrape >> t_add
