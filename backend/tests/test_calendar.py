from datetime import datetime, timezone


def test_list_events(auth_client, fake_db):
    start = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    fake_db.queue_fetchall([{
        "id": 1, "title": "삼성전자 2Q 실적발표 대기", "event_type": "earnings", "ticker": "005930",
        "start_at": start, "end_at": end, "notes": "메모", "is_ai_recommended": False,
        "priority": "HIGH", "status": "planned",
    }])

    res = auth_client.get("/api/calendar/events")

    assert res.status_code == 200
    body = res.json()[0]
    assert body["start"] == start.isoformat()
    assert body["end"] == end.isoformat()
    assert body["is_ai_recommended"] is False


def test_add_event_missing_fields(auth_client):
    res = auth_client.post("/api/calendar/events", json={"title": "제목만 있음"})
    assert res.status_code == 400
    assert res.json()["message"] == "title, start, end는 필수입니다."


def test_add_event(auth_client, fake_db):
    fake_db.queue_fetchone({"id": 7})

    res = auth_client.post("/api/calendar/events", json={
        "title": "SK하이닉스 매수 검토",
        "start": "2026-05-26T10:00:00+09:00",
        "end": "2026-05-26T11:00:00+09:00",
        "priority": "MEDIUM",
    })

    assert res.status_code == 201
    assert res.json() == {"id": 7}


def test_delete_event(auth_client, fake_db):
    res = auth_client.delete("/api/calendar/events/9")
    assert res.status_code == 200
    assert res.json() == {"message": "삭제 완료"}
