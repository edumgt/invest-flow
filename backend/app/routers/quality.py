import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..security import require_auth
from ..services import quality_service

router = APIRouter(prefix="/api/quality", tags=["quality"])


class TrainingDataBody(BaseModel):
    filename: str | None = None
    base64: str | None = None
    split: str = "train"
    label: str | None = None


class ClassifyBody(BaseModel):
    base64: str | None = None
    mimeType: str = "image/jpeg"


@router.get("/original")
async def get_original():
    result = quality_service.get_original()
    if result is None:
        raise HTTPException(status_code=404, detail="원본 이미지를 찾을 수 없습니다.")
    return result


@router.post("/training-data", status_code=201)
async def post_training_data(body: TrainingDataBody):
    if not body.filename or not body.base64 or not body.label:
        raise HTTPException(status_code=400, detail="filename, base64, label 필수")
    if body.label not in ("y", "n"):
        raise HTTPException(status_code=400, detail="label 은 y 또는 n")

    try:
        saved = await asyncio.to_thread(
            quality_service.save_training_data, body.filename, body.base64, body.split, body.label
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"saved": saved}


@router.get("/training-data")
async def get_training_data():
    return await asyncio.to_thread(quality_service.list_training_data)


@router.post("/config")
async def post_config(body: dict):
    try:
        saved = await asyncio.to_thread(quality_service.save_config, body)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    return {"saved": saved}


@router.get("/config")
async def get_config():
    return await asyncio.to_thread(quality_service.get_config)


@router.post("/classify")
async def classify(body: ClassifyBody, payload: dict = Depends(require_auth)):
    if not body.base64:
        raise HTTPException(status_code=400, detail="base64 이미지 데이터 필요")

    try:
        return await asyncio.to_thread(quality_service.classify_image, body.base64, body.mimeType)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"분류 오류: {err}")
