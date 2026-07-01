def test_list_investments_requires_auth(client):
    res = client.get("/api/investments")
    assert res.status_code == 401


def test_list_investments(auth_client, fake_db):
    fake_db.queue_fetchall([
        {"id": 1, "ticker": "AAPL", "asset_name": "Apple Inc.", "asset_type": "stock",
         "quantity": 8, "avg_price": 182.0, "currency": "USD"},
    ])

    res = auth_client.get("/api/investments")

    assert res.status_code == 200
    assert res.json() == [{
        "id": 1, "ticker": "AAPL", "asset_name": "Apple Inc.", "asset_type": "stock",
        "quantity": 8.0, "avg_price": 182.0, "currency": "USD",
    }]


def test_add_investment(auth_client, fake_db):
    fake_db.queue_fetchone({"id": 42})

    res = auth_client.post("/api/investments", json={
        "ticker": "NVDA", "asset_name": "NVIDIA", "quantity": 3, "avg_price": 780,
    })

    assert res.status_code == 201
    assert res.json() == {"id": 42}


def test_add_investment_missing_fields(auth_client):
    res = auth_client.post("/api/investments", json={"ticker": "NVDA"})
    assert res.status_code == 400


def test_delete_investment(auth_client, fake_db):
    res = auth_client.delete("/api/investments/5")
    assert res.status_code == 200
    assert res.json() == {"message": "삭제 완료"}
    # user_id 조건이 함께 걸렸는지 확인 (다른 사용자 데이터 삭제 방지)
    query, params = fake_db.queries[-1]
    assert params == (5, 1)
