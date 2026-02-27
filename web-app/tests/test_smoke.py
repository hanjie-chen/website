def test_homepage_returns_200(client):
    # Smoke test: app is up and root route is reachable.
    response = client.get("/")
    assert response.status_code == 200
