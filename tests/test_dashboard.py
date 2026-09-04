def _configure_dashboard(monkeypatch):
    monkeypatch.setenv("DASHBOARD_SUPERUSER_KEY", "admin-secret")


def test_dashboard_admin_sees_all_and_user_is_scoped(api, monkeypatch):
    _configure_dashboard(monkeypatch)

    admin_login = api.post("/dashboard/login", json={"key": "admin-secret"})
    assert admin_login.status_code == 200
    admin_data = api.get(
        "/dashboard/data",
        headers={"Authorization": f"Bearer {admin_login.json()['token']}"},
    )
    assert admin_data.status_code == 200
    assert admin_data.json()["role"] == "admin"
    assert "api-user" in {user["id"] for user in admin_data.json()["users"]}

    user_login = api.post("/dashboard/login", json={"key": "api-user"})
    assert user_login.status_code == 200
    user_data = api.get(
        "/dashboard/data",
        headers={"Authorization": f"Bearer {user_login.json()['token']}"},
    )
    assert user_data.status_code == 200
    assert user_data.json()["role"] == "user"
    assert all(item["user"] == "api-user" for item in user_data.json()["rules"])


def test_dashboard_rejects_invalid_key_and_unauthorized_data(api, monkeypatch):
    _configure_dashboard(monkeypatch)

    assert api.post("/dashboard/login", json={"key": "wrong"}).status_code == 401
    assert api.get("/dashboard/data").status_code == 401


def test_dashboard_is_read_only(api, monkeypatch):
    _configure_dashboard(monkeypatch)
    login = api.post("/dashboard/login", json={"key": "admin-secret"})
    token = login.json()["token"]

    assert (
        api.post(
            "/dashboard/users",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 404
    )
