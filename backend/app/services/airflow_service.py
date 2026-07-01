import base64

import httpx

from .. import config

_AUTH_HEADER = "Basic " + base64.b64encode(
    f"{config.AIRFLOW_USER}:{config.AIRFLOW_PASS}".encode()
).decode()


async def af_fetch(path: str, method: str = "GET", json: dict | None = None) -> tuple[int, dict]:
    url = f"{config.AIRFLOW_URL}/api/v1{path}"
    async with httpx.AsyncClient() as client:
        res = await client.request(
            method,
            url,
            json=json,
            headers={"Authorization": _AUTH_HEADER, "Content-Type": "application/json"},
        )
    try:
        body = res.json()
    except ValueError:
        body = {"error": "JSON parse failed"}
    return res.status_code, body
