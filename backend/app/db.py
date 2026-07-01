from contextlib import contextmanager

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from . import config

_pool: pool.SimpleConnectionPool | None = None


def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(1, 10, dsn=config.DATABASE_URL)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def get_cursor(commit: bool = False):
    """psycopg2 커넥션을 풀에서 빌려와 RealDictCursor를 제공한다."""
    assert _pool is not None, "DB pool not initialized"
    conn = _pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def check_connection() -> None:
    with get_cursor() as cur:
        cur.execute("SELECT 1;")
