from __future__ import annotations

import re
from pathlib import Path

from doc2md.models.document import BlockType, Document


def _strip_heading(line: str) -> str:
    return re.sub(r"^#+\s*", "", line).strip()


def _dedup_lines(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    seen: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            result.append(line)
            continue
        plain = _strip_heading(s)
        dup = False
        for prev in seen:
            p = _strip_heading(prev)
            if plain == p:
                dup = True
                break
            if len(plain) > 5 and plain in p:
                dup = True
                break
            if len(p) > 5 and p in plain:
                dup = True
                break
            if len(p) > 5 and len(plain) > 5:
                max_c = min(len(p), len(plain))
                for i in range(max_c, 4, -1):
                    if p[-i:] == plain[:i]:
                        dup = True
                        break
                if dup:
                    break
        if not dup:
            result.append(line)
            seen.append(s)
    return "\n".join(result)


class MarkdownWriter:
    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images

    def write(self, doc: Document, output_path: str) -> None:
        lines: list[str] = []
        if doc.metadata:
            lines.append("---")
            for k, v in doc.metadata.items():
                if v:
                    lines.append(f"{k}: {v}")
            lines.append("---")
            lines.append("")
        for block in doc.blocks:
            md = self._render_block(block)
            if md:
                lines.append(md)
        output = "\n".join(lines)
        output = self._post_process(output)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")

    @staticmethod
    def _post_process(text: str) -> str:
        text = text.replace("## 2C", "## I2C")
        text = _dedup_lines(text)
        return text

    def _render_block(self, block) -> str:
        match block.type:
            case BlockType.HEADING:
                return f"{'#' * min(max(block.level, 1), 6)} {block.content}"
            case BlockType.PARAGRAPH | BlockType.TABLE | BlockType.IMAGE | BlockType.RAW_TEXT:
                return block.content
            case BlockType.LIST_ITEM:
                prefix = "  " * max(0, block.level - 1)
                return f"{prefix}- {block.content}"
            case BlockType.CODE_BLOCK:
                lang = block.metadata.get("language", "")
                return f"```{lang}\n{block.content}\n```"
            case BlockType.BLOCKQUOTE:
                return f"> {block.content}"
            case BlockType.HORIZONTAL_RULE:
                return "---"
            case _:
                return block.content
