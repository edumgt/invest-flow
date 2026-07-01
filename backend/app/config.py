import os

PORT = int(os.environ.get("PORT", "3000"))
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-secret")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# CORS_ORIGIN 은 쉼표 구분 다중 오리진 허용 (예: http://localhost:5173,http://localhost:8302)
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGIN", "*").split(",") if o.strip()]

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://172.29.32.1:11300")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:latest")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llava:34b")

AIRFLOW_URL = os.environ.get("AIRFLOW_URL", "http://192.168.253.149:8793")
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.environ.get("AIRFLOW_PASS", "admin")

DATA_ROOT = os.environ.get("DATA_ROOT", "/home/ubuntu/invest-flow/DATA-ROOT")
