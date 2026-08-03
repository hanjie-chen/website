import json

import pytest
from bs4 import BeautifulSoup

import app as app_module
from daily_briefs import BriefValidationError, load_current_brief, store_brief


def brief_payload(date_label="2026-07-25", item_id="49038433"):
    return {
        "schema_version": 2,
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
                        "content_status": "ok",
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
        load_current_brief(tmp_path)["sections"]["ai"]["items"][0]["summary"]
        == "Updated summary"
    )
    assert json.loads((tmp_path / "current.json").read_text()) == {"date": "2026-07-25"}
    assert not list(tmp_path.glob("*.tmp"))


def test_unchanged_publish_repairs_current_pointer_and_removes_v1(tmp_path):
    payload = brief_payload()
    store_brief(tmp_path, payload)
    (tmp_path / "current.json").unlink()
    legacy = brief_payload("2026-07-24", "24")
    legacy["schema_version"] = 1
    (tmp_path / "2026-07-24.json").write_text(json.dumps(legacy), encoding="utf-8")

    status, _ = store_brief(tmp_path, payload)

    assert status == "unchanged"
    assert load_current_brief(tmp_path)["date"] == "2026-07-25"
    assert not (tmp_path / "2026-07-24.json").exists()


def test_store_brief_rejects_v1_missing_status_and_unknown_item_fields(tmp_path):
    schema_v1 = brief_payload()
    schema_v1["schema_version"] = 1
    missing_status = brief_payload()
    del missing_status["sections"]["ai"]["items"][0]["content_status"]
    invalid_status = brief_payload()
    invalid_status["sections"]["ai"]["items"][0]["content_status"] = "unknown"
    unknown_field = brief_payload()
    unknown_field["sections"]["ai"]["items"][0]["unexpected"] = True

    with pytest.raises(BriefValidationError, match="unsupported schema_version"):
        store_brief(tmp_path, schema_v1)
    with pytest.raises(BriefValidationError, match="exact schema v2 fields"):
        store_brief(tmp_path, missing_status)
    with pytest.raises(BriefValidationError, match="unsupported content_status"):
        store_brief(tmp_path, invalid_status)
    with pytest.raises(BriefValidationError, match="exact schema v2 fields"):
        store_brief(tmp_path, unknown_field)


@pytest.mark.parametrize("invalid_status", [None, [], 1])
def test_store_brief_rejects_non_string_content_status(tmp_path, invalid_status):
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["content_status"] = invalid_status

    with pytest.raises(BriefValidationError, match="unsupported content_status"):
        store_brief(tmp_path, payload)


def test_store_brief_keeps_seven_newest_v2_payloads_and_removes_v1(tmp_path):
    legacy = brief_payload("2026-07-19", "19")
    legacy["schema_version"] = 1
    (tmp_path / "2026-07-19.json").write_text(json.dumps(legacy), encoding="utf-8")

    for day in range(20, 28):
        store_brief(tmp_path, brief_payload(f"2026-07-{day}", str(day)))

    stored_dates = sorted(path.stem for path in tmp_path.glob("2026-*.json"))
    assert stored_dates == [f"2026-07-{day}" for day in range(21, 28)]
    assert json.loads((tmp_path / "current.json").read_text()) == {"date": "2026-07-27"}


def test_current_pointer_only_moves_forward(tmp_path):
    store_brief(tmp_path, brief_payload("2026-07-25", "25"))
    store_brief(tmp_path, brief_payload("2026-07-24", "24"))

    assert load_current_brief(tmp_path)["date"] == "2026-07-25"
    assert (tmp_path / "2026-07-24.json").is_file()


def test_load_current_brief_does_not_scan_when_pointer_is_missing_or_corrupt(
    tmp_path, caplog
):
    store_brief(tmp_path, brief_payload())
    (tmp_path / "current.json").unlink()
    assert load_current_brief(tmp_path) is None

    (tmp_path / "current.json").write_text("{broken", encoding="utf-8")
    assert load_current_brief(tmp_path) is None
    assert "status=invalid_current" in caplog.text


def test_load_current_brief_does_not_fallback_when_target_is_corrupt(tmp_path):
    store_brief(tmp_path, brief_payload("2026-07-24", "24"))
    store_brief(tmp_path, brief_payload("2026-07-25", "25"))
    (tmp_path / "2026-07-25.json").write_text("{broken", encoding="utf-8")

    assert load_current_brief(tmp_path) is None


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


def test_brief_routes_render_only_current_and_keep_history_private(client, app):
    with app.app_context():
        store_brief(
            app_module.Daily_Briefs_Directory,
            brief_payload("2026-07-24", "49038432"),
        )
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    current = client.get("/zh/briefs")
    detail = client.get("/zh/briefs/2026-07-25")
    english = client.get("/en/briefs/2026-07-25")
    private_history = client.get("/zh/briefs/2026-07-24")

    assert current.status_code == 200
    current_soup = BeautifulSoup(current.get_data(as_text=True), "html.parser")
    assert current_soup.select_one("h1 time").get_text(strip=True) == "2026-07-25"
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
    assert private_history.status_code == 404


def test_homepage_shows_latest_brief_and_language_scoped_links(client, app):
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    chinese = client.get("/zh/").get_data(as_text=True)
    english = client.get("/en/").get_data(as_text=True)

    assert 'href="/zh/briefs"' in chinese
    assert 'href="/en/briefs"' in english
    assert "最新一期： 2026-07-25" in chinese


def test_empty_current_brief_still_returns_200(client):
    response = client.get("/zh/briefs")

    assert response.status_code == 200
    assert "第一期简报尚未发布" in response.get_data(as_text=True)
