def test_root_redirect_prefers_cookie_over_accept_language(client):
    client.set_cookie("preferred_language", "en")
    response = client.get(
        "/",
        headers={
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/en"


def test_root_redirect_uses_accept_language_when_cookie_missing(client):
    response = client.get(
        "/",
        headers={
            "Accept-Language": "en-US,en;q=0.9,zh;q=0.8",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/en"


def test_root_redirect_falls_back_to_default_language_for_invalid_cookie_and_unsupported_header(
    client,
):
    client.set_cookie("preferred_language", "fr")
    response = client.get(
        "/",
        headers={
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/zh"
