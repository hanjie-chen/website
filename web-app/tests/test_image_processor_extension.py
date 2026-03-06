import markdown

from custom_md_extensions import Image_Processor_Extension


def test_image_processor_adds_bootstrap_centering_classes():
    md = markdown.Markdown(
        extensions=[
            Image_Processor_Extension(base_url="/rendered-articles/test-category/")
        ]
    )

    html = md.convert("![cover](./images/cover.png)")

    assert 'src="/rendered-articles/test-category/images/cover.png"' in html
    assert 'class="img-fluid d-block mx-auto"' in html
