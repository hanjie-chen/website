import json

from bs4 import BeautifulSoup

import app as app_module
from daily_briefs import list_briefs, load_brief, store_brief


def brief_payload(date_label="2026-07-25", item_id="49038433"):
    return {
        "schema_version": 1,
        "date": date_label,
        "generated_at": f"{date_label}T08:04:00+08:00",
        "timezone": "Asia/Singapore",
        "sections": {
            "ai": {
                "note": "",
                "items": [
                    {
                        "hn_item_id": item_id,
                        "title": "Claude <script>alert('x')</script>",
                        "summary": "支持 `code`、引号、<尖括号> 与中文标点。",
                        "why": "keywords: Claude",
                        "source_url": "https://example.com/story",
                        "discussion_url": f"https://news.ycombinator.com/item?id={item_id}",
                        "points": 1213,
                        "comments": 660,
                    }
                ],
            },
            "non_ai_hot": {"note": "", "items": []},
        },
    }


def post_brief(client, payload, token="secret-token"):
    return client.post(
        "/internal/briefs",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-DAILY-BRIEF-TOKEN": token},
    )


def test_store_brief_creates_updates_and_keeps_same_date_idempotent(tmp_path):
    payload = brief_payload()

    created, _ = store_brief(tmp_path, payload)
    unchanged, _ = store_brief(tmp_path, payload)
    payload["sections"]["ai"]["items"][0]["summary"] = "Updated summary"
    updated, _ = store_brief(tmp_path, payload)

    assert created == "created"
    assert unchanged == "unchanged"
    assert updated == "updated"
    assert (
        load_brief(tmp_path, "2026-07-25")["sections"]["ai"]["items"][0]["summary"]
        == "Updated summary"
    )
    assert not list(tmp_path.glob("*.tmp"))


def test_list_briefs_sorts_descending_and_ignores_corrupt_files(tmp_path, caplog):
    store_brief(tmp_path, brief_payload("2026-07-24", "1"))
    store_brief(tmp_path, brief_payload("2026-07-25", "2"))
    (tmp_path / "2026-07-26.json").write_text("{broken", encoding="utf-8")
    (tmp_path / "not-a-date.json").write_text("{}", encoding="utf-8")

    briefs = list_briefs(tmp_path)

    assert [brief["date"] for brief in briefs] == ["2026-07-25", "2026-07-24"]
    assert "status=invalid" in caplog.text


def test_publish_endpoint_is_hidden_without_configured_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "")

    response = post_brief(client, brief_payload())

    assert response.status_code == 404


def test_publish_endpoint_rejects_wrong_token_and_non_json(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")

    wrong = post_brief(client, brief_payload(), token="wrong")
    non_json = client.post(
        "/internal/briefs",
        data="not json",
        headers={"X-DAILY-BRIEF-TOKEN": "secret-token"},
    )

    assert wrong.status_code == 403
    assert non_json.status_code == 415


def test_publish_endpoint_creates_and_updates_same_date(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    payload = brief_payload()

    created = post_brief(client, payload)
    unchanged = post_brief(client, payload)
    payload["sections"]["ai"]["items"][0]["summary"] = "Corrected"
    updated = post_brief(client, payload)

    assert created.status_code == 201
    assert created.get_json() == {"status": "created", "date": "2026-07-25"}
    assert unchanged.status_code == 200
    assert unchanged.get_json()["status"] == "unchanged"
    assert updated.status_code == 200
    assert updated.get_json()["status"] == "updated"


def test_publish_endpoint_validates_hn_id_urls_and_empty_briefs(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    mismatch = brief_payload()
    mismatch["sections"]["ai"]["items"][0]["discussion_url"] = (
        "https://news.ycombinator.com/item?id=999"
    )
    dangerous = brief_payload()
    dangerous["sections"]["ai"]["items"][0]["source_url"] = "javascript:alert(1)"
    empty = brief_payload()
    empty["sections"]["ai"]["items"] = []

    mismatch_response = post_brief(client, mismatch)
    dangerous_response = post_brief(client, dangerous)
    empty_response = post_brief(client, empty)

    assert mismatch_response.status_code == 400
    assert "match hn_item_id" in mismatch_response.get_json()["error"]
    assert dangerous_response.status_code == 400
    assert "HTTP(S) URL" in dangerous_response.get_json()["error"]
    assert empty_response.status_code == 400
    assert "at least one item" in empty_response.get_json()["error"]


def test_publish_endpoint_rejects_oversized_body(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")

    response = client.post(
        "/internal/briefs",
        data=json.dumps({"padding": "x" * (129 * 1024)}),
        content_type="application/json",
        headers={"X-DAILY-BRIEF-TOKEN": "secret-token"},
    )

    assert response.status_code == 413


def test_brief_routes_render_archive_detail_language_notice_and_escaped_content(
    client, app
):
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    archive = client.get("/zh/briefs")
    detail = client.get("/zh/briefs/2026-07-25")
    english = client.get("/en/briefs/2026-07-25")
    missing = client.get("/zh/briefs/2026-07-24")

    assert archive.status_code == 200
    archive_soup = BeautifulSoup(archive.get_data(as_text=True), "html.parser")
    assert len(archive_soup.find_all("time", string="2026-07-25")) == 1
    detail_html = detail.get_data(as_text=True)
    detail_soup = BeautifulSoup(detail_html, "html.parser")
    assert detail.status_code == 200
    assert detail_soup.select_one("h1 time").get_text(strip=True) == "2026-07-25"
    assert not detail_soup.select(
        ".briefs-overline, .briefs-facts, .brief-section-index, .brief-item-number"
    )
    assert 'class="brief-story-title" href="https://example.com/story"' in detail_html
    assert len(detail_soup.find_all("a", href="https://example.com/story")) == 1
    assert (
        len(
            detail_soup.find_all(
                "a", href="https://news.ycombinator.com/item?id=49038433"
            )
        )
        == 1
    )
    assert "HN #49038433" not in detail_html
    assert "1,213" not in detail_html
    assert "1213 points" in detail_html
    assert "660 条评论" in detail_html
    assert "&lt;script&gt;alert" in detail_html
    assert "<script>alert" not in detail_html
    assert 'rel="noopener noreferrer"' in detail_html
    assert english.status_code == 200
    assert "currently published in Chinese only" in english.get_data(as_text=True)
    assert missing.status_code == 404


def test_homepage_shows_latest_brief_and_language_scoped_links(client, app):
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    chinese = client.get("/zh/").get_data(as_text=True)
    english = client.get("/en/").get_data(as_text=True)

    assert 'href="/zh/briefs/2026-07-25"' in chinese
    assert 'href="/en/briefs/2026-07-25"' in english
    assert "最新一期： 2026-07-25" in chinese


def test_empty_archive_still_returns_200(client):
    response = client.get("/zh/briefs")

    assert response.status_code == 200
    assert "第一期简报尚未发布" in response.get_data(as_text=True)
