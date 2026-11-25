def test_login_ok(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "alice", "password": "alice-pass"}
    )
    assert r.status_code == 200 and r.json()["access_token"]


def test_login_wrong_password(client):
    assert client.post(
        "/api/auth/login",
        data={"username": "alice", "password": "nope"}
    ).status_code == 401


def test_login_unknown_user_same_error(client):
    assert client.post(
        "/api/auth/login",
        data={"username": "ghost", "password": "x"}
    ).status_code == 401


def test_login_validation(client):
    assert client.post(
        "/api/auth/login",
        data={"username": "", "password": "x"}
    ).status_code == 422


def test_protected_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/agent/chat", json={"message": "hi"}).status_code == 401


def test_garbage_token_rejected(client):
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer abc.def.ghi"}
    ).status_code == 401