from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response

from ..security import require_auth
from ..services.airflow_service import af_fetch

router = APIRouter(prefix="/api/airflow", tags=["airflow"], dependencies=[Depends(require_auth)])


def _proxy(status: int, body: dict, response: Response):
    response.status_code = status
    return body


@router.get("/dags")
async def list_dags(request: Request, response: Response):
    qs = str(request.query_params)
    path = f"/dags?limit=100{'&' + qs if qs else ''}"
    status, body = await af_fetch(path)
    return _proxy(status, body, response)


@router.get("/dags/{dag_id}")
async def get_dag(dag_id: str, response: Response):
    status, body = await af_fetch(f"/dags/{dag_id}")
    return _proxy(status, body, response)


@router.get("/dags/{dag_id}/runs")
async def get_dag_runs(dag_id: str, request: Request, response: Response):
    limit = request.query_params.get("limit", "10")
    status, body = await af_fetch(f"/dags/{dag_id}/dagRuns?limit={limit}&order_by=-start_date")
    return _proxy(status, body, response)


@router.get("/dags/{dag_id}/runs/{run_id}/tasks")
async def get_run_tasks(dag_id: str, run_id: str, response: Response):
    status, body = await af_fetch(f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances")
    return _proxy(status, body, response)


@router.post("/dags/{dag_id}/trigger")
async def trigger_dag(dag_id: str, response: Response):
    now = datetime.now(timezone.utc).isoformat()
    status, body = await af_fetch(
        f"/dags/{dag_id}/dagRuns", method="POST", json={"dag_run_id": f"manual__{now}", "conf": {}}
    )
    return _proxy(status, body, response)


@router.post("/dags/{dag_id}/pause")
async def pause_dag(dag_id: str, response: Response):
    status, body = await af_fetch(f"/dags/{dag_id}", method="PATCH", json={"is_paused": True})
    return _proxy(status, body, response)


@router.post("/dags/{dag_id}/unpause")
async def unpause_dag(dag_id: str, response: Response):
    status, body = await af_fetch(f"/dags/{dag_id}", method="PATCH", json={"is_paused": False})
    return _proxy(status, body, response)
