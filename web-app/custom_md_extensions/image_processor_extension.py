# Point relative image paths at the note's copied assets in the rendered tree.

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor


def is_relative_reference(url: str) -> bool:
    """True for paths like "./a.png", "images/a.png" or "../b.md#x".

    Absolute URLs, root paths, protocol-relative URLs, data URIs and bare
    fragments are left alone.
    """
    if not url or url.startswith(("/", "#")):
        return False
    return not urlsplit(url).scheme


class Image_Processor(Postprocessor):
    def __init__(self, md, base_url):
        super().__init__(md)
        self.base_url = base_url

    def run(self, text):
        # Sizing and centering come from the .article-body img styles.
        soup = BeautifulSoup(text, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if is_relative_reference(src):
                img["src"] = urljoin(self.base_url, src)
        return str(soup)


class Image_Processor_Extension(Extension):
    @staticmethod
    def normalize_base_url(url: str) -> str:
        return "/" + url.strip("/") + "/"

    def __init__(self, base_url: str, **kwargs):
        """
        :param base_url: Base URL for images, e.g. 'rendered-articles/tools-git/'
        """
        base_url = Image_Processor_Extension.normalize_base_url(base_url)
        self.config = {"base_url": [base_url, "Base URL for images"]}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        base_url = self.getConfig("base_url")
        md.postprocessors.register(
            Image_Processor(md, base_url), "image_path_postprocessor", 25
        )


def makeExtension(**kwargs):
    return Image_Processor_Extension(**kwargs)
