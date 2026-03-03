# This extension is improved from https://github.com/dahlia/markdown-gfm-admonition
# I do a little improved and plan to give a PR after a while 2025-02-07

# future plan: submit a PR
# I need to improve the Readme.md to specified how to use it, and how to define the css style

import re
from typing import List, Optional

from markdown.core import Markdown
from markdown.extensions import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.blockparser import BlockParser
from xml.etree.ElementTree import Element, SubElement


class Gfm_Admonition_Processor(BlockProcessor):
    PATTERN = re.compile(
        r"""
        ^\s*                                                # 可能的前导空白
        \[!\s*(note|tip|important|warning|caution)\s*\]     # 匹配 admonition 标签，支持小写
        (?:$|\s*\n)                                         # 行尾或者换行
    """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __init__(self, parser: BlockParser):
        super().__init__(parser)

    def test(self, parent: Element, block: str) -> bool:
        if parent.tag != "blockquote":
            return False
        match = self.PATTERN.match(block)
        return match is not None

    def run(self, parent: Element, blocks: List[str]) -> Optional[bool]:
        if not blocks:
            return False
        match = self.PATTERN.match(blocks[0])
        if not match:
            return False

        # 去掉匹配部分，剩下的内容会作为内部块内容
        blocks[0] = blocks[0][match.end() :]
        admonition_type = match.group(1).lower()  # 统一转换为小写

        # 将原来的 blockquote 改为 div，并设置 CSS 类方便样式定制
        parent.tag = "div"
        parent.set("class", f"admonition {admonition_type}")

        # 添加一个标题子节点
        title = SubElement(parent, "p")
        title.set("class", "admonition-title")
        title.text = admonition_type.capitalize()

        # 将剩余块内容继续解析到这个 div 中
        self.parser.parseBlocks(parent, blocks)
        blocks.clear()

        return True


class Gfm_Admonition_Extension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        md.registerExtension(self)
        md.parser.blockprocessors.register(
            Gfm_Admonition_Processor(md.parser), "gfm_admonition", 105
        )


def make_Extension(**kwargs):
    return Gfm_Admonition_Extension(**kwargs)
