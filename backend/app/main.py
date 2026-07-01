from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db
from .routers import ai, airflow, auth, calendar, investments, quality


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_pool()
    yield
    db.close_pool()


app = FastAPI(title="Investment Advisor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in config.CORS_ORIGINS else config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"message": "잘못된 요청 형식입니다."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"message": str(exc) or "서버 오류가 발생했습니다."})


@app.get("/health")
def health():
    try:
        db.check_connection()
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=500, content={"status": "db_error"})


app.include_router(auth.router)
app.include_router(investments.router)
app.include_router(calendar.router)
app.include_router(ai.router)
app.include_router(airflow.router)
app.include_router(quality.router)
