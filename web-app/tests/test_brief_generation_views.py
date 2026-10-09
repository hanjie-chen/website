from datetime import date

import pytest
from bs4 import BeautifulSoup
from test_daily_briefs import brief_payload, brief_provenance

import app as app_module
import daily_briefs


def generation_info():
    return {
        "materials": {
            "webpage": {
                "status": "failed",
                "method": "jina",
                "origin": "unknown",
                "reason": "cloudflare_challenge",
            },
            "hn_post": {"status": "empty", "reason": "none"},
            "hn_comments": {"status": "success", "reason": "none"},
        },
        "summary_sources": ["hn_comments"],
        "generation": {
            "status": "success",
            "model": "provider/actual-fallback-model",
            "reason": "none",
        },
    }


def render_info(client, monkeypatch, info, lang="zh"):
    monkeypatch.setattr(daily_briefs, "_brief_today", lambda: date(2026, 7, 27))
    payload = brief_payload()
    item = payload["sections"]["ai"]["items"][0]
    # Conflicting legacy information must not override the richer record.
    item["provenance"] = brief_provenance()
    item["generation_info"] = info
    daily_briefs.store_brief(app_module.Daily_Briefs_Directory, payload)
    response = client.get(f"/{lang}/briefs/2026-07-25")
    assert response.status_code == 200
    return BeautifulSoup(response.get_data(as_text=True), "html.parser")


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_acquisition_failure_does_not_hide_successful_comment_summary(
    client, monkeypatch, lang
):
    soup = render_info(client, monkeypatch, generation_info(), lang)
    details = soup.select_one(".brief-details")
    assert not details.has_attr("open")
    assert len(details.select(".brief-material-list li")) == 3
    text = details.get_text(" ", strip=True)
    assert "provider/actual-fallback-model" in text
    assert "Cloudflare" in text
    assert "Jina Reader" in text
    assert "keywords: Claude" in text  # Selection basis is retained.
    assert "briefs.generation." not in text
    if lang == "zh":
        assert "网页：获取失败" in text
        assert "HN 帖子：无内容" in text
        assert "HN 评论：成功" in text
        assert "模型报告" in text
        assert "生成情况： 成功" in text
        assert "摘要依据：" not in text
    else:
        assert "Generation info" in text
        assert "Generation: Succeeded" in text
        assert "Reported by the model" in text


@pytest.mark.parametrize("sources", [None, ["web_metadata", "web_body", "hn_post"]])
def test_sources_are_not_inferred_from_available_comments(client, monkeypatch, sources):
    info = generation_info()
    info["summary_sources"] = sources
    soup = render_info(client, monkeypatch, info)
    row = soup.find("dt", string="摘要来源：").find_next_sibling("dd")
    text = row.get_text(" ", strip=True)
    assert "HN 评论" not in text
    if sources is None:
        assert text == "未记录"
        assert "模型报告" not in text
    else:
        assert "网页元信息、网页正文、HN 帖子" in text


@pytest.mark.parametrize(
    ("status", "reason", "expected"),
    [
        ("insufficient", "source_material_insufficient", "材料不足"),
        ("failed", "rate_limited", "请求受限或额度耗尽"),
        ("not_attempted", "no_materials", "未尝试"),
        ("unknown", "none", "未记录"),
    ],
)
def test_summary_outcomes_have_separate_localized_explanations(
    client, monkeypatch, status, reason, expected
):
    info = generation_info()
    info["generation"] = {"status": status, "model": None, "reason": reason}
    info["summary_sources"] = None if status == "unknown" else []
    soup = render_info(client, monkeypatch, info)
    row = soup.find("dt", string="生成情况：").find_next_sibling("dd")
    assert expected in row.get_text()
    assert "provider/" not in row.get_text()


def test_recovery_reason_is_not_reported_as_final_fetch_failure(client, monkeypatch):
    info = generation_info()
    info["materials"]["webpage"].update(status="success", origin="same_article")
    info["summary_sources"] = ["web_body", "hn_comments"]
    soup = render_info(client, monkeypatch, info)
    webpage = soup.select_one(".brief-material-list li").get_text(" ", strip=True)
    assert "网页：成功" in webpage
    assert "同一篇文章" in webpage
    assert "替代获取原因：Cloudflare 验证" in webpage
    assert "最后尝试" not in webpage
