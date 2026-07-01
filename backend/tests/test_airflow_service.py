import httpx
import respx

from app import config
from app.services import airflow_service


async def test_af_fetch_success(monkeypatch):
    monkeypatch.setattr(config, "AIRFLOW_URL", "http://fake-airflow")

    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://fake-airflow/api/v1/dags").mock(
            return_value=httpx.Response(200, json={"dags": []})
        )
        status, body = await airflow_service.af_fetch("/dags")

    assert status == 200
    assert body == {"dags": []}


async def test_af_fetch_non_json_response(monkeypatch):
    monkeypatch.setattr(config, "AIRFLOW_URL", "http://fake-airflow")

    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://fake-airflow/api/v1/dags").mock(
            return_value=httpx.Response(500, content=b"internal error", headers={"content-type": "text/plain"})
        )
        status, body = await airflow_service.af_fetch("/dags")

    assert status == 500
    assert body == {"error": "JSON parse failed"}
