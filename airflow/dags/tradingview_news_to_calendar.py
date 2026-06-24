"""
tradingview_news_to_calendar.py
================================
TradingView 한국 블로그(https://www.tradingview.com/blog/ko/)에서
5분마다 최신 뉴스를 수집하여 InvestFlow 캘린더에 이벤트로 추가합니다.

중복 방지: 기사 URL의 포스트 ID를 이벤트 제목에 포함시켜 판단합니다.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

BLOG_URL    = "https://www.tradingview.com/blog/ko/"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://192.168.253.148:3000")
TV_USER     = os.environ.get("BACKEND_USER", "test1")
TV_PASS     = os.environ.get("BACKEND_PASS", "123456")

KST = timezone(timedelta(hours=9))

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────────────

def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_date(date_str: str) -> datetime:
    """'Jun 16' 형식 → KST datetime. 연도는 현재 연도 사용."""
    m = re.match(r"(\w{3})\s+(\d{1,2})", date_str.strip())
    if not m:
        return datetime.now(KST)
    month = MONTH_MAP.get(m.group(1), datetime.now().month)
    day   = int(m.group(2))
    year  = datetime.now().year
    return datetime(year, month, day, 9, 0, tzinfo=KST)


def _parse_articles(html: str) -> list[dict]:
    """
    <article ... class="... post-XXXXX ..."> 블록을 분리해 파싱합니다.
    각 블록에서 URL / 제목 / 날짜 / 카테고리를 추출합니다.
    """
    articles = []
    blocks = re.split(r"<article\s+", html)[1:]   # 첫 빈 요소 제외

    for block in blocks:
        # 포스트 ID (id="post-58839" 또는 class="... post-58839 ..." 둘 다 처리)
        pid_m = re.search(r"post-(\d{4,})", block)
        if not pid_m:
            continue
        post_id = int(pid_m.group(1))

        # 기사 URL
        url_m = re.search(
            r'href="(https://www\.tradingview\.com/blog/ko/[a-z0-9\-]+-\d{4,}/)"',
            block,
        )
        if not url_m:
            continue

        # 제목: <h2|h3 class="title"> 직접 추출 (특집=h2, 일반=h3)
        title_m = re.search(r'<h[23][^>]*class="title"[^>]*>([\s\S]+?)</h[23]>', block)
        title = _strip_tags(title_m.group(1)).strip() if title_m else ""

        # 날짜
        date_m = re.search(r'class="date"[^>]*>([^<]+)</div>', block)
        pub_dt = _parse_date(date_m.group(1)) if date_m else datetime.now(KST)

        # 카테고리
        cat_m = re.search(r'class="tv-category-link">([^<]+)</a>', block)
        category = cat_m.group(1).strip() if cat_m else "뉴스"

        if not title:
            continue

        articles.append({
            "post_id":  post_id,
            "url":      url_m.group(1),
            "title":    title[:200],
            "pub_dt":   pub_dt,
            "category": category,
        })

    articles.sort(key=lambda x: x["post_id"], reverse=True)
    return articles


# ── Task 함수 ────────────────────────────────────────────────────────────────

def scrape_news(**context) -> list[dict]:
    """TradingView 블로그 스크래핑"""
    resp = requests.get(BLOG_URL, headers=SCRAPE_HEADERS, timeout=20)
    resp.raise_for_status()

    articles = _parse_articles(resp.text)
    log.info("스크래핑 완료: %d개 기사", len(articles))
    for a in articles[:5]:
        log.info("  [%d] %s (%s)", a["post_id"], a["title"][:60], a["category"])

    # xcom에 직렬화 가능한 형태로 저장
    serializable = [
        {**a, "pub_dt": a["pub_dt"].isoformat()}
        for a in articles
    ]
    context["ti"].xcom_push(key="articles", value=serializable)
    return serializable


def add_to_calendar(**context) -> None:
    """스크래핑된 뉴스를 캘린더 이벤트로 추가 (중복 제외)"""
    articles = context["ti"].xcom_pull(key="articles", task_ids="scrape_news") or []
    if not articles:
        log.warning("추가할 기사 없음")
        return

    # ── 로그인 ──
    login = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": TV_USER, "password": TV_PASS},
        timeout=10,
    )
    login.raise_for_status()
    token = login.json()["token"]
    auth  = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ── 기존 이벤트 조회 (중복 방지) ──
    existing_resp = requests.get(f"{BACKEND_URL}/api/calendar/events", headers=auth, timeout=10)
    existing_ids: set[int] = set()
    if existing_resp.ok:
        for ev in existing_resp.json():
            m = re.search(r"\[TV-(\d+)\]", ev.get("title", ""))
            if m:
                existing_ids.add(int(m.group(1)))
    log.info("기존 TV 이벤트 ID: %s", sorted(existing_ids))

    # ── 신규 기사만 추가 ──
    added = 0
    for article in articles:
        if article["post_id"] in existing_ids:
            log.info("이미 존재 [%d]: %s", article["post_id"], article["title"][:40])
            continue

        try:
            pub_dt = datetime.fromisoformat(article["pub_dt"])
        except Exception:
            pub_dt = datetime.now(KST)

        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=KST)

        title   = f"[TV-{article['post_id']}] {article['title']}"
        start   = pub_dt.isoformat()
        end     = (pub_dt + timedelta(hours=1)).isoformat()
        notes   = f"{article['category']} | {article['url']}"

        payload = {
            "title":            title[:200],
            "event_type":       "general",
            "ticker":           None,
            "start":            start,
            "end":              end,
            "notes":            notes,
            "is_ai_recommended": False,
            "priority":         "LOW",
        }

        resp = requests.post(
            f"{BACKEND_URL}/api/calendar/events",
            json=payload,
            headers=auth,
            timeout=10,
        )
        if resp.ok:
            log.info("✅ 추가 [%d]: %s", article["post_id"], article["title"][:50])
            added += 1
        else:
            log.warning("❌ 실패 (%d) [%d]: %s", resp.status_code, article["post_id"], resp.text[:100])

    log.info("완료: %d개 신규 이벤트 추가", added)


# ── DAG 정의 ─────────────────────────────────────────────────────────────────

default_args: dict = {
    "owner":            "airflow",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=2),
}

with DAG(
    dag_id="tradingview_news_to_calendar",
    default_args=default_args,
    description="TradingView KO 블로그 뉴스 → InvestFlow 캘린더 자동 추가 (5분 주기)",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["news", "tradingview", "calendar", "scraping"],
) as dag:

    t_scrape = PythonOperator(
        task_id="scrape_news",
        python_callable=scrape_news,
    )

    t_add = PythonOperator(
        task_id="add_to_calendar",
        python_callable=add_to_calendar,
    )

    t_scrape >> t_add
