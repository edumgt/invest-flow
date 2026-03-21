"""
calendar_pipeline_dag.py
========================
GitLab 파이프라인 실행 및 모니터링 DAG

이 DAG는 Apache Airflow에서 GitLab CI/CD 파이프라인을 오케스트레이션합니다.

기능:
  - GitLab 프로젝트에 새 파이프라인을 트리거
  - 파이프라인 완료(성공/실패)까지 폴링
  - 파이프라인 결과를 Airflow 태스크 상태로 반영
  - 스케줄 실행 및 외부 API 호출(수동 트리거) 지원

환경 변수 / Airflow Variables:
  - GITLAB_URL        : GitLab 인스턴스 URL (예: http://gitlab.local:8080)
  - GITLAB_TOKEN      : GitLab Personal Access Token (api scope)
  - GITLAB_PROJECT_ID : 대상 GitLab 프로젝트 ID 또는 경로

Airflow Connections (선택):
  - gitlab_default    : HTTP Connection으로 등록 시 환경변수보다 우선

사용 예:
  # Airflow UI에서 수동 트리거 (conf 파라미터 예시)
  {
    "branch": "main",
    "variables": {"DEPLOY_ENV": "staging"}
  }
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 설정값 (Airflow Variable 또는 환경변수에서 로드)
# ─────────────────────────────────────────────
def _get_config(key: str, default: str = "") -> str:
    """Airflow Variable → 환경변수 순으로 설정값을 조회합니다."""
    try:
        return Variable.get(key)
    except Exception:
        return os.environ.get(key, default)


GITLAB_URL = _get_config("GITLAB_URL", "http://gitlab.local:8080")
GITLAB_TOKEN = _get_config("GITLAB_TOKEN", "")
GITLAB_PROJECT_ID = _get_config("GITLAB_PROJECT_ID", "")

# 파이프라인 폴링 설정
POLL_INTERVAL_SECONDS = 30
PIPELINE_TIMEOUT_SECONDS = 3600  # 1시간

# ─────────────────────────────────────────────
# GitLab API 헬퍼
# ─────────────────────────────────────────────

def _gitlab_headers() -> dict[str, str]:
    """GitLab API 인증 헤더를 반환합니다."""
    if not GITLAB_TOKEN:
        raise AirflowException(
            "GITLAB_TOKEN이 설정되지 않았습니다. "
            "Airflow Variable 'GITLAB_TOKEN' 또는 환경변수를 설정하세요."
        )
    return {
        "PRIVATE-TOKEN": GITLAB_TOKEN,
        "Content-Type": "application/json",
    }


def _project_api_base() -> str:
    """GitLab 프로젝트 API base URL을 반환합니다."""
    if not GITLAB_PROJECT_ID:
        raise AirflowException(
            "GITLAB_PROJECT_ID가 설정되지 않았습니다. "
            "Airflow Variable 'GITLAB_PROJECT_ID' 또는 환경변수를 설정하세요."
        )
    # 프로젝트 경로(namespace/project)인 경우 URL 인코딩
    import urllib.parse
    encoded = urllib.parse.quote(str(GITLAB_PROJECT_ID), safe="")
    return f"{GITLAB_URL}/api/v4/projects/{encoded}"


# ─────────────────────────────────────────────
# Task 함수들
# ─────────────────────────────────────────────

def trigger_gitlab_pipeline(**context: Any) -> dict[str, Any]:
    """
    GitLab 프로젝트에 파이프라인을 트리거합니다.

    dag_run.conf 파라미터:
      - branch    : 대상 브랜치 (기본값: main)
      - variables : 파이프라인 변수 dict (선택)
    """
    dag_run_conf = context.get("dag_run").conf or {}
    ref = dag_run_conf.get("branch", "main")
    pipeline_variables = dag_run_conf.get("variables", {})

    payload: dict[str, Any] = {"ref": ref}
    if pipeline_variables:
        payload["variables"] = [
            {"key": k, "value": v} for k, v in pipeline_variables.items()
        ]

    api_url = f"{_project_api_base()}/pipeline"
    log.info("GitLab 파이프라인 트리거: %s (ref=%s)", api_url, ref)

    resp = requests.post(
        api_url,
        headers=_gitlab_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    pipeline = resp.json()

    pipeline_id = pipeline["id"]
    pipeline_url = pipeline.get("web_url", "")
    log.info("파이프라인 생성 완료: id=%s, url=%s", pipeline_id, pipeline_url)

    # XCom에 파이프라인 정보 저장
    context["ti"].xcom_push(key="pipeline_id", value=pipeline_id)
    context["ti"].xcom_push(key="pipeline_url", value=pipeline_url)

    return {"pipeline_id": pipeline_id, "pipeline_url": pipeline_url, "ref": ref}


def monitor_gitlab_pipeline(**context: Any) -> str:
    """
    GitLab 파이프라인 완료까지 폴링합니다.

    성공 시  : "success" 반환
    실패 시  : AirflowException 발생
    타임아웃 : AirflowException 발생
    """
    pipeline_id = context["ti"].xcom_pull(key="pipeline_id", task_ids="trigger_pipeline")
    if not pipeline_id:
        raise AirflowException("pipeline_id를 XCom에서 찾을 수 없습니다.")

    api_url = f"{_project_api_base()}/pipelines/{pipeline_id}"
    log.info("파이프라인 모니터링 시작: id=%s", pipeline_id)

    terminal_statuses = {"success", "failed", "canceled", "skipped"}
    elapsed = 0

    while elapsed < PIPELINE_TIMEOUT_SECONDS:
        resp = requests.get(api_url, headers=_gitlab_headers(), timeout=30)
        resp.raise_for_status()
        pipeline = resp.json()

        status = pipeline.get("status", "unknown")
        log.info("[%ds] 파이프라인 상태: %s", elapsed, status)

        if status in terminal_statuses:
            if status == "success":
                log.info("파이프라인 성공! id=%s", pipeline_id)
                return "success"
            else:
                raise AirflowException(f"파이프라인 {status}: id={pipeline_id}")

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    raise AirflowException(
        f"파이프라인 타임아웃 ({PIPELINE_TIMEOUT_SECONDS}s): id={pipeline_id}"
    )


def fetch_pipeline_jobs(**context: Any) -> list[dict[str, Any]]:
    """
    완료된 파이프라인의 잡 목록과 상태를 조회하여 XCom에 저장합니다.
    """
    pipeline_id = context["ti"].xcom_pull(key="pipeline_id", task_ids="trigger_pipeline")
    api_url = f"{_project_api_base()}/pipelines/{pipeline_id}/jobs"

    resp = requests.get(api_url, headers=_gitlab_headers(), timeout=30)
    resp.raise_for_status()
    jobs = resp.json()

    summary = [
        {
            "id": j["id"],
            "name": j["name"],
            "stage": j["stage"],
            "status": j["status"],
            "duration": j.get("duration"),
            "web_url": j.get("web_url"),
        }
        for j in jobs
    ]
    log.info("파이프라인 잡 요약:\n%s", json.dumps(summary, indent=2, ensure_ascii=False))
    context["ti"].xcom_push(key="jobs_summary", value=summary)
    return summary


def report_pipeline_result(**context: Any) -> None:
    """
    파이프라인 결과를 로그로 출력하고 알림을 발송합니다.
    (슬랙/이메일 알림은 Airflow Connection 설정 후 확장 가능)
    """
    pipeline_id = context["ti"].xcom_pull(key="pipeline_id", task_ids="trigger_pipeline")
    pipeline_url = context["ti"].xcom_pull(key="pipeline_url", task_ids="trigger_pipeline")
    jobs_summary = context["ti"].xcom_pull(key="jobs_summary", task_ids="fetch_jobs") or []

    success_jobs = [j for j in jobs_summary if j["status"] == "success"]
    failed_jobs = [j for j in jobs_summary if j["status"] == "failed"]

    report = (
        f"\n{'='*60}\n"
        f"  GitLab 파이프라인 결과 보고서\n"
        f"{'='*60}\n"
        f"  파이프라인 ID : {pipeline_id}\n"
        f"  URL          : {pipeline_url}\n"
        f"  성공 잡      : {len(success_jobs)}/{len(jobs_summary)}\n"
        f"  실패 잡      : {len(failed_jobs)}\n"
        f"{'='*60}"
    )
    log.info(report)

    if failed_jobs:
        log.warning("실패한 잡: %s", [j["name"] for j in failed_jobs])


# ─────────────────────────────────────────────
# DAG 정의
# ─────────────────────────────────────────────

default_args: dict[str, Any] = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="calendar_app_pipeline",
    default_args=default_args,
    description="Vue Calendar App GitLab CI/CD 파이프라인 오케스트레이션",
    # 매일 새벽 2시 자동 실행 (KST 기준 — UTC+9 이므로 UTC 17:00)
    schedule_interval="0 17 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["gitlab", "ci-cd", "calendar-app"],
    doc_md=__doc__,
) as dag:

    trigger_pipeline = PythonOperator(
        task_id="trigger_pipeline",
        python_callable=trigger_gitlab_pipeline,
        doc_md="GitLab 파이프라인을 트리거합니다.",
    )

    monitor_pipeline = PythonOperator(
        task_id="monitor_pipeline",
        python_callable=monitor_gitlab_pipeline,
        execution_timeout=timedelta(seconds=PIPELINE_TIMEOUT_SECONDS + 60),
        doc_md="파이프라인이 완료될 때까지 상태를 폴링합니다.",
    )

    fetch_jobs = PythonOperator(
        task_id="fetch_jobs",
        python_callable=fetch_pipeline_jobs,
        doc_md="파이프라인 잡 목록과 상태를 조회합니다.",
    )

    report_result = PythonOperator(
        task_id="report_result",
        python_callable=report_pipeline_result,
        doc_md="파이프라인 결과를 보고합니다.",
    )

    # Task 의존성 체인
    trigger_pipeline >> monitor_pipeline >> fetch_jobs >> report_result
