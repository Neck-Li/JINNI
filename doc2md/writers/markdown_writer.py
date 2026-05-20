from __future__ import annotations

import re
from pathlib import Path

from doc2md.models.document import BlockType, Document


def _strip_heading(line: str) -> str:
    """Remove '#' heading prefix for comparison purposes."""
    return re.sub(r"^#+\s*", "", line).strip()


def _dedup_lines(text: str) -> str:
    """Remove duplicate or overlapping lines (track last non-empty line)."""
    lines = text.split("\n")
    result: list[str] = []
    last_raw = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue
        # Compare without heading prefix
        plain = _strip_heading(stripped)
        if plain == _strip_heading(last_raw):
            continue
        if last_raw and _overlap_ratio(_strip_heading(last_raw), plain) > 0.4:
            continue
        result.append(line)
        last_raw = stripped
    return "\n".join(result)


def _overlap_ratio(a: str, b: str) -> float:
    """How much of the shorter string is contained in the longer one."""
    if not a or not b:
        return 0.0
    shorter = a if len(a) < len(b) else b
    longer = b if len(a) < len(b) else a
    if len(shorter) < 10:
        return 1.0 if shorter == longer else 0.0
    if shorter in longer:
        return len(shorter) / len(longer)
    return 0.0


class MarkdownWriter:
    """Renders a Document model to a .md file."""

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
        """Post-processing fixes for common PDF extraction artifacts."""
        text = text.replace("## 2C", "## I2C")
        text = _dedup_lines(text)
        return text

    def _render_block(self, block) -> str:
        match block.type:
            case BlockType.HEADING:
                level = min(max(block.level, 1), 6)
                return f"{'#' * level} {block.content}"

            case BlockType.PARAGRAPH:
                return block.content

            case BlockType.TABLE:
                return block.content

            case BlockType.IMAGE:
                return block.content

            case BlockType.LIST_ITEM:
                prefix = "  " * max(0, block.level - 1)
                marker = "- " if block.level < 2 else "* "
                return f"{prefix}{marker}{block.content}"

            case BlockType.CODE_BLOCK:
                lang = block.metadata.get("language", "")
                return f"```{lang}\n{block.content}\n```"

            case BlockType.BLOCKQUOTE:
                return f"> {block.content}"

            case BlockType.HORIZONTAL_RULE:
                return "---"

            case BlockType.RAW_TEXT:
                return block.content

            case _:
                return block.content
