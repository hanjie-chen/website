from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


def test_mobile_topbar_participates_in_document_flow():
    css = (APP_DIR / "static/css/style.css").read_text(encoding="utf-8")
    mobile_css = css.split("@media (max-width: 768px)", maxsplit=1)[1]

    assert ".navbar-custom.fixed-top" in mobile_css
    assert "position: sticky" in mobile_css
    assert ".main-content" in mobile_css
    assert "padding-top: 0.75rem" in mobile_css
