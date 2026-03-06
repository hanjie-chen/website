def test_homepage_returns_200(client):
    # Smoke test: app is up and root route is reachable.
    response = client.get("/")
    assert response.status_code == 200


def test_homepage_static_assets_are_versioned(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "/static/css/style.css?v=" in html
    assert "/static/bootstrap5/js/bootstrap.bundle.min.js?v=" in html
    assert "/static/images/headavatar/head_avatar_problem.png?v=" in html
