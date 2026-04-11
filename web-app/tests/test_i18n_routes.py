import pytest

from i18n import get_language_from_header


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


@pytest.mark.parametrize("path", ["/en-US", "/english", "/zh-Hant"])
def test_homepage_rejects_non_canonical_language_paths(client, path):
    response = client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/zh", "/en"])
def test_homepage_accepts_canonical_language_paths(client, path):
    response = client.get(path)

    assert response.status_code == 200


def test_accept_language_prefers_higher_q_value():
    assert get_language_from_header("zh-CN;q=0.4,en-US;q=0.9") == "en"
