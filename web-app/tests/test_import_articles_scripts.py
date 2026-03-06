from import_articles_scripts import divide_files_and_folders


def test_divide_files_and_folders_ignores_hidden_template_dirs(tmp_path):
    (tmp_path / "__template__").mkdir()
    (tmp_path / ".drafts").mkdir()
    (tmp_path / "public").mkdir()
    (tmp_path / "article.md").write_text("content", encoding="utf-8")

    files, folders = divide_files_and_folders(str(tmp_path))

    assert files == ["article.md"]
    assert folders == ["public"]
