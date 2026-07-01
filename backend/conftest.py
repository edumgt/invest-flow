from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.main import app
from app.security import require_auth

TEST_USER = {"sub": 1, "username": "alice", "displayName": "Alice Kim"}


class FakeCursor:
    """psycopg2 RealDictCursor 흉내: execute 호출을 기록하고 미리 큐에 넣은 결과를 반환한다."""

    def __init__(self, fake_db: "FakeDB"):
        self._fake_db = fake_db

    def execute(self, query, params=None):
        self._fake_db.queries.append((query, params))

    def fetchone(self):
        return self._fake_db._pop(self._fake_db.one_results)

    def fetchall(self):
        return self._fake_db._pop(self._fake_db.all_results, default=[])


class FakeDB:
    def __init__(self):
        self.queries: list[tuple] = []
        self.one_results: list = []
        self.all_results: list = []
        self.raise_error: Exception | None = None

    def queue_fetchone(self, value):
        self.one_results.append(value)

    def queue_fetchall(self, value):
        self.all_results.append(value)

    @staticmethod
    def _pop(queue, default=None):
        return queue.pop(0) if queue else default

    def get_cursor(self, commit: bool = False):
        @contextmanager
        def _cm():
            if self.raise_error:
                raise self.raise_error
            yield FakeCursor(self)

        return _cm()


@pytest.fixture
def fake_db(monkeypatch):
    fdb = FakeDB()
    monkeypatch.setattr(db_module, "get_cursor", fdb.get_cursor)
    return fdb


@pytest.fixture
def client(monkeypatch):
    # 실제 Postgres 커넥션 풀 생성을 건너뛴다 (테스트에선 fake_db 로 대체).
    monkeypatch.setattr(db_module, "init_pool", lambda: None)
    monkeypatch.setattr(db_module, "close_pool", lambda: None)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    app.dependency_overrides[require_auth] = lambda: TEST_USER
    yield client
    app.dependency_overrides.pop(require_auth, None)
