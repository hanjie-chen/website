import pytest

import app as app_module


def test_reindex_returns_404_when_token_not_configured(client, monkeypatch):
    # Endpoint is hidden (404) when server token is not configured.
    monkeypatch.setattr(app_module, "REIMPORT_ARTICLES_TOKEN", "")
    response = client.post("/internal/reindex")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-REIMPORT-ARTICLES-TOKEN": "wrong-token"},
        {"X-REIMPORT-ARTICLES-TOKEN": "été"},
    ],
)
def test_reindex_returns_403_on_missing_wrong_or_non_ascii_token(
    client, monkeypatch, headers
):
    # Missing, wrong or non-ASCII header tokens should be rejected, never a 500.
    monkeypatch.setattr(app_module, "REIMPORT_ARTICLES_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "import_articles", lambda *_args, **_kwargs: None)

    response = client.post("/internal/reindex", headers=headers)
    assert response.status_code == 403


def test_reindex_returns_200_on_valid_token(client, monkeypatch):
    # Valid token should trigger import pipeline and return success JSON.
    called = {"import_called": False}

    def fake_import_articles(*_args, **_kwargs):
        called["import_called"] = True

    monkeypatch.setattr(app_module, "REIMPORT_ARTICLES_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "import_articles", fake_import_articles)

    response = client.post(
        "/internal/reindex",
        headers={"X-REIMPORT-ARTICLES-TOKEN": "secret-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert called["import_called"] is True
