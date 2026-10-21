# Turn links between notes into knowledge-base paths the note page resolves.
#
# A note links another by its Markdown path ("../ssh/client-guide.md"), while
# the site serves notes by id. Rendering cannot know ids (the target may not be
# imported yet), so links become NOTE_LINK_PREFIX + the target's path from the
# knowledge base root, and the note view swaps that for the target's page URL.

import posixpath
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor

NOTE_LINK_PREFIX = "/notes/path/"


def note_link_target(href: str, note_dir: str) -> str | None:
    """Return the linked note's path from the root, or None for other links.

    Paths starting with "/" are read from the knowledge base root, as GitHub
    reads them inside a repository.
    """
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or not parts.path.lower().endswith(".md"):
        return None
    if parts.path.startswith("/"):
        target = posixpath.normpath(parts.path.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(note_dir, parts.path))
    if target.startswith("../") or target == "..":
        return None
    return target


class Note_Link_Processor(Postprocessor):
    def __init__(self, md, note_dir):
        super().__init__(md)
        self.note_dir = note_dir

    def run(self, text):
        soup = BeautifulSoup(text, "html.parser")
        for link in soup.find_all("a", href=True):
            target = note_link_target(link["href"], self.note_dir)
            if target is None:
                continue
            fragment = urlsplit(link["href"]).fragment
            link["href"] = (
                NOTE_LINK_PREFIX + quote(target) + (f"#{fragment}" if fragment else "")
            )
        return str(soup)


class Note_Link_Extension(Extension):
    def __init__(self, note_dir: str, **kwargs):
        """
        :param note_dir: The linking note's folder from the root, e.g. 'tools/git'
        """
        self.config = {"note_dir": [note_dir.replace("\\", "/"), "Note folder"]}
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.postprocessors.register(
            Note_Link_Processor(md, self.getConfig("note_dir")),
            "note_link_postprocessor",
            24,
        )


def makeExtension(**kwargs):
    return Note_Link_Extension(**kwargs)
