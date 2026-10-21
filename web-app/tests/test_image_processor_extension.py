import markdown

from custom_md_extensions import Image_Processor_Extension


def test_image_processor_rewrites_relative_src_without_layout_classes():
    md = markdown.Markdown(
        extensions=[
            Image_Processor_Extension(base_url="/rendered-articles/test-category/")
        ]
    )

    html = md.convert("![cover](./images/cover.png)")

    assert 'src="/rendered-articles/test-category/images/cover.png"' in html
    assert "class=" not in html


def test_image_processor_rewrites_every_relative_path_but_leaves_absolute_ones():
    md = markdown.Markdown(
        extensions=[Image_Processor_Extension(base_url="/rendered-articles/tools-git/")]
    )

    html = md.convert(
        "![a](images/a.png) ![b](../shared/b.png) ![c](/static/c.png)"
        " ![d](https://example.com/d.png)"
    )

    assert 'src="/rendered-articles/tools-git/images/a.png"' in html
    assert 'src="/rendered-articles/shared/b.png"' in html
    assert 'src="/static/c.png"' in html
    assert 'src="https://example.com/d.png"' in html
