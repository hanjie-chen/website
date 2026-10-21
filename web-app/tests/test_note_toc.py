import note_views


def test_build_note_toc_assigns_ids_and_extracts_outline():
    # The title left the body, so its outline starts at h2 and shows as level 1.
    html = "<h2>Intro</h2><p>Text</p><h3>Setup</h3><h3>Setup</h3><h4>中文 标题</h4>"

    updated_html, toc_items = note_views.build_note_toc(html)

    assert 'id="intro"' in updated_html
    assert 'id="setup"' in updated_html
    assert 'id="setup-2"' in updated_html
    assert 'id="中文-标题"' in updated_html
    assert toc_items == [
        {
            "id": "intro",
            "text": "Intro",
            "level": 1,
            "children": [
                {"id": "setup", "text": "Setup", "level": 2, "children": []},
                {
                    "id": "setup-2",
                    "text": "Setup",
                    "level": 2,
                    "children": [
                        {
                            "id": "中文-标题",
                            "text": "中文 标题",
                            "level": 3,
                            "children": [],
                        }
                    ],
                },
            ],
        }
    ]


def test_build_note_toc_keeps_orphan_subheadings_visible():
    html = "<h3>Setup</h3><h4>Commands</h4>"

    _, toc_items = note_views.build_note_toc(html)

    assert toc_items == [
        {
            "id": "setup",
            "text": "Setup",
            "level": 2,
            "children": [
                {"id": "commands", "text": "Commands", "level": 3, "children": []}
            ],
        }
    ]
