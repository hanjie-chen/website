import app as app_module


def test_build_article_toc_assigns_ids_and_extracts_outline():
    html = "<h1>Intro</h1><p>Text</p><h2>Setup</h2><h2>Setup</h2><h3>中文 标题</h3>"

    updated_html, toc_items = app_module._build_article_toc(html)

    assert 'id="intro"' in updated_html
    assert 'id="setup"' in updated_html
    assert 'id="setup-2"' in updated_html
    assert 'id="中文-标题"' in updated_html
    assert toc_items == [
        {"id": "intro", "text": "Intro", "level": 1},
        {"id": "setup", "text": "Setup", "level": 2},
        {"id": "setup-2", "text": "Setup", "level": 2},
        {"id": "中文-标题", "text": "中文 标题", "level": 3},
    ]
