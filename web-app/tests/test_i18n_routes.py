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
    assert response.headers["Location"] == "/en/"


def test_root_redirect_uses_accept_language_when_cookie_missing(client):
    response = client.get(
        "/",
        headers={
            "Accept-Language": "en-US,en;q=0.9,zh;q=0.8",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/"


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
    assert response.headers["Location"] == "/zh/"


@pytest.mark.parametrize("path", ["/en-US", "/english", "/zh-Hant"])
def test_homepage_rejects_non_canonical_language_paths(client, path):
    response = client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/zh/", "/en/"])
def test_homepage_accepts_canonical_language_paths(client, path):
    response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("path", "expected_location"),
    [
        ("/zh", "/zh/"),
        ("/en", "/en/"),
    ],
)
def test_homepage_redirects_canonical_language_paths_without_trailing_slash(
    client, path, expected_location
):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"] == expected_location


def test_homepage_links_stay_in_current_language_namespace(client):
    response = client.get("/en/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/en/"' in body
    assert 'href="/en/articles"' in body
    assert 'href="/en/about"' in body


def test_about_page_links_stay_in_current_language_namespace(client):
    response = client.get("/en/about")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/en/about"' in body
    assert 'href="/en/"' in body
    assert 'href="/en/articles"' in body


def test_legacy_about_route_returns_404(client):
    response = client.get("/about")

    assert response.status_code == 404


def test_accept_language_prefers_higher_q_value():
    assert get_language_from_header("zh-CN;q=0.4,en-US;q=0.9") == "en"


def test_homepage_sets_dynamic_html_lang_attribute(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<html lang="zh-CN">' in html


def test_homepage_renders_language_switcher(client):
    response = client.get("/en/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/set-language/zh?next=/zh/"' in html
    assert "中文" in html
    assert "English" in html


def test_set_language_redirects_and_persists_cookie(client):
    response = client.get("/set-language/zh?next=/zh/about", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/zh/about"
    assert "preferred_language=zh" in response.headers["Set-Cookie"]
