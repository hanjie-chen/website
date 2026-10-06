import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import app as app_module
import daily_briefs
from daily_briefs import (
    BriefValidationError,
    load_brief,
    load_brief_archive,
    load_current_brief,
    prune_briefs,
    store_brief,
)
from daily_briefs import (
    _brief_today as real_brief_today,
)


@pytest.fixture(autouse=True)
def brief_clock(monkeypatch):
    clock = [date(2026, 7, 27)]
    monkeypatch.setattr(daily_briefs, "_brief_today", lambda: clock[0])
    return clock


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


def brief_provenance(**overrides):
    provenance = {
        "summary_basis": "article",
        "retrieval_method": "jina",
        "retrieval_status": "success",
        "material_origin": "original",
        "fallback_reason": "challenge_page",
    }
    provenance.update(overrides)
    return provenance


def post_brief(client, payload, token="secret-token"):
    return client.post(
        "/internal/briefs",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-DAILY-BRIEF-TOKEN": token},
    )


def test_public_brief_api_reads_published_content_without_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    latest = brief_payload("2026-07-25")
    older = brief_payload("2026-07-24")
    assert post_brief(client, latest).status_code == 201
    assert post_brief(client, older).status_code == 201

    response = client.get("/api/briefs/latest")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == latest
    assert client.get("/api/briefs/2026-07-24").get_json() == older
    assert client.get("/api/briefs").get_json() == {
        "items": [
            {
                "date": payload["date"],
                "generated_at": payload["generated_at"],
                "ai_items": 1,
                "non_ai_hot_items": 0,
            }
            for payload in (latest, older)
        ]
    }

    latest["sections"]["ai"]["items"][0]["summary"] = "修订后的摘要"
    assert post_brief(client, latest).status_code == 200
    assert client.get("/api/briefs/2026-07-25").get_json() == latest
    assert client.get("/api/briefs/latest").get_json() == latest


def test_public_brief_api_preserves_valid_provenance(client, monkeypatch):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["provenance"] = brief_provenance()

    assert post_brief(client, payload).status_code == 201
    assert client.get("/api/briefs/latest").get_json() == payload


def test_public_brief_api_empty_archive(client):
    response = client.get("/api/briefs")
    assert response.status_code == 200
    assert response.get_json() == {"items": []}


@pytest.mark.parametrize(
    "date_label", ["latest", "2026-07-25", "2026-02-30", "2026-7-25", "current.json"]
)
def test_public_brief_api_missing_or_invalid_date_returns_json(client, date_label):
    response = client.get(f"/api/briefs/{date_label}")
    assert response.status_code == 404
    assert response.get_json() == {"error": "brief_not_found"}


@pytest.mark.parametrize("path", ["", "/latest", "/2026-07-25"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_public_brief_api_rejects_writes(client, path, method):
    response = client.open(f"/api/briefs{path}", method=method, json=brief_payload())
    assert response.status_code == 405
    assert load_brief_archive(app_module.Daily_Briefs_Directory) == []


@pytest.mark.parametrize(
    ("source_url", "expected"),
    [
        ("https://claude.com/blog/article", "claude.com"),
        ("https://www.example.com:8443/story", "example.com"),
    ],
)
def test_source_hostname_uses_compact_domain(source_url, expected):
    assert app_module._source_hostname(source_url) == expected


@pytest.mark.parametrize(
    ("source_url", "expected"),
    [
        ("https://claude.com/blog/article", "Claude 官方"),
        ("https://WWW.CLAUDE.COM/blog/article", "Claude 官方"),
        ("https://claude.com/pricing", "Claude 官方"),
        ("https://claude.com.evil.example/article", "claude.com.evil.example"),
        ("https://blog.claude.com/article", "blog.claude.com"),
        ("https://www.example.com/story", "example.com"),
    ],
)
def test_source_display_name_uses_exact_official_allowlist(source_url, expected):
    assert app_module._source_display_name(source_url) == expected


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
    assert load_current_brief(tmp_path)["date"] == "2026-07-25"
    assert load_brief_archive(tmp_path) == [
        {
            "date": "2026-07-25",
            "generated_at": "2026-07-25T08:04:00+08:00",
            "ai_items": 1,
            "non_ai_hot_items": 0,
        }
    ]
    assert json.loads((tmp_path / "current.json").read_text()) == {"date": "2026-07-25"}
    assert not list(tmp_path.glob("*.tmp"))


def test_unchanged_publish_repairs_current_pointer_and_archive_index(tmp_path):
    payload = brief_payload()
    store_brief(tmp_path, payload)
    (tmp_path / "current.json").unlink()
    (tmp_path / "archive-index.json").unlink()

    status, _ = store_brief(tmp_path, payload)

    assert status == "unchanged"
    assert load_current_brief(tmp_path)["date"] == "2026-07-25"
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == ["2026-07-25"]


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


@pytest.mark.parametrize(
    "provenance",
    [
        {"summary_basis": "article"},
        {**brief_provenance(), "unexpected": "field"},
        brief_provenance(summary_basis="made_up"),
        brief_provenance(retrieval_method=1),
        brief_provenance(retrieval_status="done"),
        brief_provenance(material_origin=None),
        brief_provenance(fallback_reason="other"),
    ],
)
def test_store_brief_strictly_validates_optional_provenance(tmp_path, provenance):
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["provenance"] = provenance

    with pytest.raises(BriefValidationError, match="provenance"):
        store_brief(tmp_path, payload)


@pytest.mark.parametrize("invalid_status", [None, [], 1])
def test_store_brief_rejects_non_string_content_status(tmp_path, invalid_status):
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["content_status"] = invalid_status

    with pytest.raises(BriefValidationError, match="unsupported content_status"):
        store_brief(tmp_path, payload)


def test_store_brief_retains_and_indexes_every_payload_in_window(tmp_path):
    for day in range(18, 28):
        store_brief(tmp_path, brief_payload(f"2026-07-{day}", str(day)))

    stored_dates = sorted(path.stem for path in tmp_path.glob("2026-*.json"))
    assert stored_dates == [f"2026-07-{day}" for day in range(18, 28)]
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == [
        f"2026-07-{day}" for day in range(27, 17, -1)
    ]
    assert json.loads((tmp_path / "current.json").read_text()) == {"date": "2026-07-27"}


def test_current_pointer_only_moves_forward(tmp_path):
    store_brief(tmp_path, brief_payload("2026-07-25", "25"))
    store_brief(tmp_path, brief_payload("2026-07-24", "24"))

    assert load_current_brief(tmp_path)["date"] == "2026-07-25"
    assert (tmp_path / "2026-07-24.json").is_file()
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == [
        "2026-07-25",
        "2026-07-24",
    ]


def test_same_date_update_refreshes_archive_metadata(tmp_path):
    payload = brief_payload()
    store_brief(tmp_path, payload)
    payload["generated_at"] = "2026-07-25T09:30:00+08:00"
    payload["sections"]["non_ai_hot"]["items"] = payload["sections"]["ai"]["items"]
    payload["sections"]["ai"]["items"] = []

    status, _ = store_brief(tmp_path, payload)

    assert status == "updated"
    assert load_brief_archive(tmp_path) == [
        {
            "date": "2026-07-25",
            "generated_at": "2026-07-25T09:30:00+08:00",
            "ai_items": 0,
            "non_ai_hot_items": 1,
        }
    ]


def test_archive_reads_only_the_index_without_falling_back_to_payload_scan(
    tmp_path, caplog
):
    store_brief(tmp_path, brief_payload())
    (tmp_path / "archive-index.json").unlink()

    assert load_brief_archive(tmp_path) == []
    assert load_brief(tmp_path, "2026-07-25")["date"] == "2026-07-25"

    (tmp_path / "archive-index.json").write_text("{broken", encoding="utf-8")
    assert load_brief_archive(tmp_path) == []
    assert "status=invalid_archive_index" in caplog.text


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
    non_ascii = post_brief(client, brief_payload(), token="été")
    non_json = client.post(
        "/internal/briefs",
        data="not json",
        headers={"X-DAILY-BRIEF-TOKEN": "secret-token"},
    )

    assert wrong.status_code == 403
    assert non_ascii.status_code == 403
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


def test_brief_routes_render_archive_and_historical_details(client, app):
    current_payload = brief_payload()
    current_payload["sections"]["ai"]["items"][0]["source_url"] = (
        "https://claude.com/blog/article"
    )
    with app.app_context():
        store_brief(
            app_module.Daily_Briefs_Directory,
            brief_payload("2026-07-24", "49038432"),
        )
        store_brief(app_module.Daily_Briefs_Directory, current_payload)

    archive = client.get("/zh/briefs")
    english_archive = client.get("/en/briefs")
    detail = client.get("/zh/briefs/2026-07-25")
    english = client.get("/en/briefs/2026-07-25")
    historical = client.get("/zh/briefs/2026-07-24")

    assert archive.status_code == 200
    archive_soup = BeautifulSoup(archive.get_data(as_text=True), "html.parser")
    assert (
        archive_soup.select_one(".briefs-lead").get_text(strip=True)
        == "每天从计算与软件领域及少量圈外探索中筛选值得阅读的内容，减少信息噪声。"
    )
    assert [
        time.get_text(strip=True) for time in archive_soup.select(".brief-date")
    ] == [
        "2026-07-25",
        "2026-07-24",
    ]
    assert [
        " ".join(meta.get_text().split())
        for meta in archive_soup.select(".brief-archive-meta")
    ] == [
        "1 技术精选 · 0 圈外",
        "1 技术精选 · 0 圈外",
    ]
    assert english_archive.status_code == 200
    english_archive_soup = BeautifulSoup(
        english_archive.get_data(as_text=True), "html.parser"
    )
    assert (
        english_archive_soup.select_one(".briefs-lead").get_text(strip=True)
        == "A small daily selection from computing and software, plus a few "
        "beyond-the-bubble discoveries, curated to reduce information noise."
    )
    assert [
        " ".join(meta.get_text().split())
        for meta in english_archive_soup.select(".brief-archive-meta")
    ] == [
        "1 Tech picks · 0 Beyond",
        "1 Tech picks · 0 Beyond",
    ]
    detail_html = detail.get_data(as_text=True)
    detail_soup = BeautifulSoup(detail_html, "html.parser")
    assert detail.status_code == 200
    assert detail_soup.select_one("h1 time").get_text(strip=True) == "2026-07-25"
    assert (
        detail_soup.select_one("#brief-section-ai").get_text(strip=True) == "技术精选"
    )
    assert not detail_soup.select(
        ".briefs-overline, .briefs-facts, .brief-section-index, .brief-item-number"
    )
    assert (
        'class="brief-story-title" href="https://claude.com/blog/article"'
        in detail_html
    )
    source_name = detail_soup.select_one(".brief-source-name")
    assert source_name.get_text(strip=True) == "Claude 官方"
    assert source_name.name == "span"
    assert len(detail_soup.find_all("a", href="https://claude.com/blog/article")) == 1
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
    english_html = english.get_data(as_text=True)
    assert "currently published in Chinese only" in english_html
    assert "Tech picks" in english_html
    assert historical.status_code == 200
    assert "2026-07-24" in historical.get_data(as_text=True)


def date_step_links(soup, container):
    return [
        (link["rel"], link["href"], link["aria-label"])
        for link in soup.select(f"{container} a.brief-date-step")
    ]


def test_brief_detail_links_adjacent_archived_briefs_in_hero_and_topbar_dock(
    client, app
):
    # 2026-07-23 has no brief, so steps must skip archive gaps.
    with app.app_context():
        for date_label in ("2026-07-22", "2026-07-24", "2026-07-25"):
            store_brief(app_module.Daily_Briefs_Directory, brief_payload(date_label))

    middle = BeautifulSoup(
        client.get("/zh/briefs/2026-07-24").get_data(as_text=True), "html.parser"
    )
    expected = [
        (["prev"], "/zh/briefs/2026-07-22", "上一期: 2026-07-22"),
        (["next"], "/zh/briefs/2026-07-25", "下一期: 2026-07-25"),
    ]
    assert date_step_links(middle, ".brief-date-row") == expected
    assert date_step_links(middle, ".navbar-custom .brief-dock") == expected
    assert middle.select_one(".brief-date-row h1 time")["datetime"] == "2026-07-24"

    back_to_top = middle.select_one(".navbar-custom .brief-dock-date")
    assert back_to_top["href"] == "#brief-top"
    assert back_to_top["aria-label"] == "2026-07-24 · 回到顶部"
    assert middle.select_one("#brief-top").select_one(".brief-date-row")
    assert back_to_top.select_one(".brief-dock-date-full").get_text() == "2026-07-24"
    assert back_to_top.select_one(".brief-dock-date-short").get_text() == "07-24"
    assert back_to_top.select_one(".brief-dock-date-arrow")["aria-hidden"] == "true"

    newest = BeautifulSoup(
        client.get("/en/briefs/2026-07-25").get_data(as_text=True), "html.parser"
    )
    assert date_step_links(newest, ".brief-date-row") == [
        (["prev"], "/en/briefs/2026-07-24", "Previous brief: 2026-07-24"),
    ]
    # An inert placeholder keeps the date centered where no newer brief exists.
    placeholder = newest.select_one(".brief-date-row .brief-date-step--newer")
    assert placeholder.name == "span"
    assert placeholder["aria-hidden"] == "true"

    oldest = BeautifulSoup(
        client.get("/zh/briefs/2026-07-22").get_data(as_text=True), "html.parser"
    )
    assert date_step_links(oldest, ".brief-dock") == [
        (["next"], "/zh/briefs/2026-07-24", "下一期: 2026-07-24"),
    ]


def test_topbar_date_dock_only_renders_on_brief_detail_pages(client, app):
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    detail = client.get("/zh/briefs/2026-07-25").get_data(as_text=True)
    assert 'class="site-nav-center"' in detail
    assert "brief-date-dock.js" in detail

    for path in ("/zh/", "/zh/briefs", "/zh/articles", "/zh/about"):
        html = client.get(path).get_data(as_text=True)
        assert 'class="site-nav-center"' not in html, path
        assert "brief-date-dock.js" not in html, path
        assert 'class="site-nav-brand-mark"' in html, path


def test_brief_route_renders_community_roundup_as_escaped_project_list(client, app):
    payload = brief_payload()
    payload["sections"]["ai"]["items"][0]["summary"] = (
        "根据 Hacker News 部分评论：以下是几位社区成员最近分享的项目。\n\n"
        "- <script>项目</script>：用 Git 追踪法律文本的修改。\n"
        "- ShopSpec：根据尺寸生成木工制作方案。"
    )
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, payload)

    stored = load_brief(app_module.Daily_Briefs_Directory, "2026-07-25")
    response = client.get("/zh/briefs/2026-07-25")
    html = response.get_data(as_text=True)
    soup = BeautifulSoup(html, "html.parser")

    assert (
        stored["sections"]["ai"]["items"][0]["summary"]
        == payload["sections"]["ai"]["items"][0]["summary"]
    )
    assert response.status_code == 200
    assert (
        soup.select_one(".brief-summary--roundup .brief-summary-lead").get_text(
            strip=True
        )
        == "根据 Hacker News 部分评论：以下是几位社区成员最近分享的项目。"
    )
    assert [
        item.get_text(strip=True) for item in soup.select(".brief-summary-list li")
    ] == [
        "<script>项目</script>：用 Git 追踪法律文本的修改。",
        "ShopSpec：根据尺寸生成木工制作方案。",
    ]
    assert "&lt;script&gt;项目&lt;/script&gt;" in html
    assert "<script>项目</script>" not in html


def test_brief_detail_keeps_provenance_collapsed_and_summary_attribution_visible(
    client, app
):
    payload = brief_payload()
    item = payload["sections"]["ai"]["items"][0]
    item["summary"] = "根据 Hacker News 部分评论：这个项目仍在早期阶段。"
    item["provenance"] = brief_provenance(
        summary_basis="source_and_comments",
        retrieval_method="jina",
        retrieval_status="failed",
        material_origin="unknown",
    )
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, payload)

    response = client.get("/zh/briefs/2026-07-25")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
    details = soup.select_one(".brief-details")

    assert response.status_code == 200
    assert details.name == "details"
    assert not details.has_attr("open")
    assert details.select_one("summary").get_text(strip=True) == "详情"
    assert "入选依据：" in details.get_text()
    assert "推荐理由：" not in soup.get_text()
    assert not soup.select(".brief-why")
    assert "页面或帖子材料与部分 HN 评论" in details.get_text()
    assert "未取得（最后尝试：Jina Reader）" in details.get_text()
    assert "通过 Jina Reader 取得" not in details.get_text()
    assert (
        "根据 Hacker News 部分评论：这个项目仍在早期阶段。"
        in soup.select_one(".brief-summary").get_text()
    )


@pytest.mark.parametrize(
    "provenance",
    [
        None,
        brief_provenance(
            summary_basis="unknown",
            retrieval_method="unknown",
            retrieval_status="unknown",
            material_origin="unknown",
            fallback_reason="unknown",
        ),
    ],
)
def test_legacy_and_unknown_provenance_do_not_invent_details(client, provenance):
    payload = brief_payload()
    item = payload["sections"]["ai"]["items"][0]
    if provenance is not None:
        item["provenance"] = provenance
    store_brief(app_module.Daily_Briefs_Directory, payload)
    response = client.get("/zh/briefs/2026-07-25")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
    details = soup.select_one(".brief-details")
    assert [label.get_text() for label in details.select("dt")] == ["入选依据："]
    assert details.select_one("dd").get_text() == item["why"]


def test_homepage_shows_latest_brief_and_language_scoped_links(client, app):
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    chinese = client.get("/zh/").get_data(as_text=True)
    english = client.get("/en/").get_data(as_text=True)

    assert 'href="/zh/briefs/2026-07-25"' in chinese
    assert 'href="/en/briefs/2026-07-25"' in english
    assert "查看全部 1 条 →" in chinese
    assert "See all 1 →" in english


@pytest.mark.parametrize(
    ("console_day", "path", "expected_label"),
    [
        (date(2026, 7, 25), "/zh/", None),
        (date(2026, 7, 26), "/zh/", "7月25日"),
        (date(2026, 7, 26), "/en/", "Jul 25"),
    ],
)
def test_homepage_labels_brief_date_only_when_it_is_not_today(
    client, app, monkeypatch, console_day, path, expected_label
):
    monkeypatch.setattr(
        app_module,
        "_console_now",
        lambda: datetime(
            console_day.year,
            console_day.month,
            console_day.day,
            9,
            tzinfo=daily_briefs.BRIEF_TIMEZONE,
        ),
    )
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, brief_payload())

    soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
    label = soup.select_one(".home-section-heading time")

    if expected_label is None:
        assert label is None
    else:
        assert label.get_text() == expected_label
        assert label["datetime"] == "2026-07-25"


def test_homepage_previews_first_two_items_in_display_order(client, app):
    payload = brief_payload()
    template = payload["sections"]["ai"]["items"][0]

    def item(item_id, title, summary):
        return {
            **template,
            "hn_item_id": item_id,
            "title": title,
            "summary": summary,
            "source_url": f"https://example.com/{item_id}",
            "discussion_url": f"https://news.ycombinator.com/item?id={item_id}",
        }

    payload["sections"]["ai"]["items"] = [item("1", "First", "第一条摘要")]
    payload["sections"]["non_ai_hot"]["items"] = [
        item("2", "Second", "第二条摘要\n\n- 换行也只占一行"),
        item("3", "Third", "第三条摘要"),
    ]
    with app.app_context():
        store_brief(app_module.Daily_Briefs_Directory, payload)

    soup = BeautifulSoup(client.get("/zh/").get_data(as_text=True), "html.parser")
    items = soup.select(".home-brief-item")

    assert [entry.select_one(".home-brief-title").get_text() for entry in items] == [
        "First",
        "Second",
    ]
    assert items[0].select_one(".home-brief-title")["href"] == "https://example.com/1"
    assert items[0].select_one(".home-brief-title")["rel"] == ["noopener", "noreferrer"]
    assert (
        items[1].select_one(".home-brief-summary").get_text().startswith("第二条摘要")
    )
    assert "Third" not in soup.get_text()
    assert (
        soup.select_one(".home-section-link").get_text(strip=True) == "查看全部 3 条 →"
    )


def test_empty_archive_still_returns_200(client):
    response = client.get("/zh/briefs")

    assert response.status_code == 200
    assert "最近 14 天暂无简报" in response.get_data(as_text=True)


def test_homepage_without_brief_points_to_archive(client):
    chinese = BeautifulSoup(client.get("/zh/").get_data(as_text=True), "html.parser")
    english = BeautifulSoup(client.get("/en/").get_data(as_text=True), "html.parser")

    assert chinese.select(".home-brief-item") == []
    assert chinese.select_one(".home-brief-empty").get_text() == "最近 14 天暂无简报"
    assert chinese.select_one(".home-section-link")["href"] == "/zh/briefs"
    assert english.select_one(".home-section-link")["href"] == "/en/briefs"


@pytest.mark.parametrize(
    "today", [date(2026, 10, 4), date(2027, 1, 5), date(2028, 3, 5)]
)
def test_retention_includes_exactly_fourteen_calendar_dates(
    tmp_path, brief_clock, today
):
    brief_clock[0] = today
    dates = [(today - timedelta(days=offset)).isoformat() for offset in range(14)]
    for date_label in dates:
        store_brief(tmp_path, brief_payload(date_label))
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == dates
    assert load_current_brief(tmp_path)["date"] == today.isoformat()
    for outside in (today - timedelta(days=14), today + timedelta(days=1)):
        with pytest.raises(BriefValidationError, match="latest 14 calendar days"):
            store_brief(tmp_path, brief_payload(outside.isoformat()))
        assert not (tmp_path / f"{outside}.json").exists()


@pytest.mark.parametrize("date_label", ["2026-07-13", "2026-07-28"])
def test_outside_window_publish_is_rejected_even_when_generated_today(
    client, monkeypatch, date_label
):
    monkeypatch.setattr(app_module, "DAILY_BRIEF_PUBLISH_TOKEN", "secret-token")
    payload = brief_payload(date_label)
    payload["generated_at"] = "2026-07-27T08:00:00+08:00"
    response = post_brief(client, payload)
    assert response.status_code == 400
    assert "latest 14 calendar days" in response.get_json()["error"]
    assert load_brief_archive(app_module.Daily_Briefs_Directory) == []


def test_reads_expire_without_upload_or_cleanup(client, brief_clock):
    root = app_module.Daily_Briefs_Directory
    store_brief(root, brief_payload("2026-07-14"))
    assert client.get("/api/briefs/latest").status_code == 200
    brief_clock[0] = date(2026, 7, 28)

    assert load_current_brief(root) is None
    assert load_brief(root, "2026-07-14") is None
    assert load_brief_archive(root) == []
    assert client.get("/api/briefs").get_json() == {"items": []}
    for path in ("/api/briefs/latest", "/api/briefs/2026-07-14"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.get_json() == {"error": "brief_not_found"}
    for lang in ("zh", "en"):
        assert client.get(f"/{lang}/briefs/2026-07-14").status_code == 404
        assert "/briefs/2026-07-14" not in client.get(f"/{lang}/").get_data(
            as_text=True
        )
    assert "最近 14 天暂无简报" in client.get("/zh/briefs").get_data(as_text=True)
    assert "No briefs in the last 14 days" in client.get("/en/briefs").get_data(
        as_text=True
    )
    # Reads hide the expired file even before physical cleanup runs.
    assert (Path(root) / "2026-07-14.json").exists()


def test_publish_cleans_expired_files_and_index(tmp_path, brief_clock):
    brief_clock[0] = date(2026, 7, 25)
    for day in (12, 13, 14, 25):
        store_brief(tmp_path, brief_payload(f"2026-07-{day}"))
    brief_clock[0] = date(2026, 7, 27)
    store_brief(tmp_path, brief_payload())

    assert sorted(path.stem for path in tmp_path.glob("2026-*.json")) == [
        "2026-07-14",
        "2026-07-25",
    ]
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == [
        "2026-07-25",
        "2026-07-14",
    ]
    assert json.loads((tmp_path / "current.json").read_text()) == {"date": "2026-07-25"}


def test_date_navigation_and_archive_drop_expired_briefs(client, brief_clock):
    for date_label in ("2026-07-14", "2026-07-15"):
        store_brief(app_module.Daily_Briefs_Directory, brief_payload(date_label))
    brief_clock[0] = date(2026, 7, 28)
    for lang in ("zh", "en"):
        detail = client.get(f"/{lang}/briefs/2026-07-15")
        assert detail.status_code == 200
        assert "/briefs/2026-07-14" not in detail.get_data(as_text=True)
        index = client.get(f"/{lang}/briefs").get_data(as_text=True)
        assert "2026-07-15" in index
        assert "2026-07-14" not in index
    assert [
        entry["date"] for entry in client.get("/api/briefs").get_json()["items"]
    ] == ["2026-07-15"]


def test_cleanup_removes_orphans_and_clears_empty_current(tmp_path, brief_clock):
    store_brief(tmp_path, brief_payload())
    (tmp_path / "2026-07-01.json").write_text("{broken")
    (tmp_path / "2026-12-01.json").write_text("{}")
    (tmp_path / "settings.json").write_text("{}")
    (tmp_path / "2026-7-01.json").write_text("{}")
    brief_clock[0] = date(2026, 8, 8)
    assert prune_briefs(tmp_path) == 3
    assert not (tmp_path / "current.json").exists()
    assert not (tmp_path / "2026-12-01.json").exists()
    assert load_brief_archive(tmp_path) == []
    assert json.loads((tmp_path / "archive-index.json").read_text())["briefs"] == []
    assert (tmp_path / "settings.json").exists()
    assert (tmp_path / "2026-7-01.json").exists()
    assert prune_briefs(tmp_path) == 0


def test_republishing_does_not_extend_date_retention(tmp_path, brief_clock):
    store_brief(tmp_path, brief_payload("2026-07-14"))
    assert store_brief(tmp_path, brief_payload("2026-07-14"))[0] == "unchanged"
    brief_clock[0] = date(2026, 7, 28)
    with pytest.raises(BriefValidationError, match="latest 14 calendar days"):
        store_brief(tmp_path, brief_payload("2026-07-14"))
    assert prune_briefs(tmp_path) == 1


def test_cleanup_preserves_boundary_and_repairs_stale_pointer(tmp_path):
    store_brief(tmp_path, brief_payload("2026-07-14"))
    (tmp_path / "current.json").write_text('{"date":"2026-07-01"}')
    (tmp_path / "2026-07-01.json").write_text("{}")
    assert prune_briefs(tmp_path) == 1
    assert load_current_brief(tmp_path)["date"] == "2026-07-14"
    assert (tmp_path / "2026-07-14.json").exists()


def test_cleanup_refuses_corrupt_archive_before_deleting_files(tmp_path):
    (tmp_path / "2026-07-01.json").write_text("{}")
    (tmp_path / "archive-index.json").write_text("{broken")
    with pytest.raises(BriefValidationError, match="valid JSON"):
        prune_briefs(tmp_path)
    assert (tmp_path / "2026-07-01.json").exists()


def test_publishing_and_cleanup_share_lock(tmp_path):
    def publish(day):
        store_brief(tmp_path, brief_payload(f"2026-07-{day}"))
        prune_briefs(tmp_path)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(publish, range(14, 28)))
    assert [entry["date"] for entry in load_brief_archive(tmp_path)] == [
        f"2026-07-{day}" for day in range(27, 13, -1)
    ]
    assert load_current_brief(tmp_path)["date"] == "2026-07-27"
    assert len(list(tmp_path.glob("2026-*.json"))) == 14
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "instant,expected",
    [
        (datetime(2026, 7, 27, 15, 59, 59, tzinfo=UTC), date(2026, 7, 27)),
        (datetime(2026, 7, 27, 16, 0, 0, tzinfo=UTC), date(2026, 7, 28)),
    ],
)
def test_brief_today_uses_singapore_midnight(monkeypatch, instant, expected):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz)

    monkeypatch.setattr(daily_briefs, "datetime", FixedDatetime)
    assert real_brief_today() == expected
