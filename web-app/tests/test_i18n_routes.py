from html import unescape

import pytest
from bs4 import BeautifulSoup

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


@pytest.mark.parametrize("path", ["/zh/", "/en/"])
def test_homepage_is_a_console_without_landing_page_sections(client, path):
    response = client.get(path)
    html = response.get_data(as_text=True)
    soup = BeautifulSoup(html, "html.parser")

    assert response.status_code == 200
    assert soup.select_one("h1").get_text(strip=True) == "hanjie site"
    assert [heading.get_text(strip=True) for heading in soup.select("h2")] == [
        "每日简报" if path == "/zh/" else "Daily Brief"
    ]
    for removed in (
        "Build, Learn, Document.",
        "PERSONAL SITE / KNOWLEDGE BASE",
        "What you&#39;ll find here",
        "Current Focus",
        "Why This Site Exists",
        "head_avatar_problem.png",
    ):
        assert removed not in html


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
    assert 'href="/en/briefs"' in body
    assert 'href="/en/about"' in body


def test_about_page_links_stay_in_current_language_namespace(client):
    response = client.get("/en/about")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/en/about"' in body
    assert 'href="/en/"' in body
    assert 'href="/en/articles"' in body
    assert 'href="/en/briefs"' in body


def test_shared_topbar_uses_fixed_brand_and_english_nav_on_chinese_homepage(client):
    response = client.get("/zh/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    brand = BeautifulSoup(body, "html.parser").select_one("a.site-nav-brand")
    assert brand["href"] == "/zh/"
    assert brand.select_one(".site-nav-brand-mark")["aria-hidden"] == "true"
    assert brand.get_text(strip=True) == "hanjie site"
    assert ">Home<" not in body
    assert ">Articles<" in body
    assert ">Brief<" in body
    assert ">About<" in body
    assert "欢迎来到我的个人网站" not in body
    assert "🏡" not in body


def test_homepage_marks_no_nav_link_active_and_labels_mobile_menu(client):
    response = client.get("/zh/")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")

    assert response.status_code == 200
    assert soup.select("a.site-nav-link.is-active") == []
    assert soup.select_one("#site-nav-toggle").get_text(strip=True) == "Menu"


def test_about_page_marks_about_link_active(client):
    response = client.get("/en/about")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    links = BeautifulSoup(body, "html.parser").select("a.site-nav-link.is-active")
    assert len(links) == 2
    assert all(
        link["href"] == "/en/about" and link["aria-current"] == "page" for link in links
    )
    assert all(link.get_text(strip=True) == "About" for link in links)


def test_chinese_about_page_keeps_hero_overline_and_removes_duplicate_section_overlines(
    client,
):
    response = client.get("/zh/about")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<p class="about-overline">PROFILE / HIRING PAGE</p>' in html
    assert "Download Resume" in html
    assert "Coming Soon" in html
    assert "Contact Me" in html
    assert "Open to opportunities" in html
    assert "Shanghai CN / Remote-friendly" in html
    assert html.count('class="about-overline"') == 1
    assert "<h2>我是谁</h2>" in html
    assert "<h2>我如何工作</h2>" in html
    assert "<h2>联系我</h2>" in html


def test_english_about_page_keeps_single_section_titles_after_overline_cleanup(client):
    response = client.get("/en/about")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<p class="about-overline">Profile / Hiring Page</p>' in html
    assert html.count('class="about-overline"') == 1
    assert "<h2>Who I Am</h2>" in html
    assert "<h2>How I Work</h2>" in html
    assert "<h2>Contact</h2>" in html


@pytest.mark.parametrize("path", ["/zh/", "/en/about"])
def test_pages_render_without_footer(client, path):
    response = client.get(path)
    html = unescape(response.get_data(as_text=True))

    assert response.status_code == 200
    assert "<footer" not in html
    assert "©" not in html


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


def test_homepage_renders_left_aligned_segmented_language_switcher_in_fixed_order(
    client,
):
    response = client.get("/en/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<div class="site-nav-identity">' in html
    assert (
        '<a href="/set-language/zh?next=/zh/" class="site-language-option">中</a>'
        in html
    )
    assert 'class="site-language-option is-active"' in html
    assert ">EN</span>" in html
    assert (
        html.index('class="site-nav-brand"')
        < html.index('class="site-language-switcher"')
        < html.index('class="site-nav-list site-nav-menu"')
    )


def test_chinese_homepage_marks_current_language_inside_segmented_switcher(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="site-language-option is-active"' in html
    assert ">中</span>" in html
    assert (
        '<a href="/set-language/en?next=/en/" class="site-language-option">EN</a>'
        in html
    )


def test_set_language_redirects_and_persists_cookie(client):
    response = client.get("/set-language/zh?next=/zh/about", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/zh/about"
    assert "preferred_language=zh" in response.headers["Set-Cookie"]


def test_set_language_rejects_external_redirect_targets(client):
    response = client.get(
        "/set-language/en?next=https://evil.example/phish",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/"
    assert "preferred_language=en" in response.headers["Set-Cookie"]


def test_set_language_rejects_protocol_relative_redirect_targets(client):
    response = client.get("/set-language/en?next=//evil.example/phish")

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/"


def test_localized_404_page_uses_english_copy(client):
    response = client.get("/en/missing-page")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Page Not Found" in html
    assert "requested URL was not found" in html


def test_localized_404_page_uses_chinese_copy(client):
    response = client.get("/zh/missing-page")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "页面不存在" in html
    assert "你访问的地址不存在" in html
