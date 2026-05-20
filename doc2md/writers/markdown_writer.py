from __future__ import annotations

from pathlib import Path

from doc2md.models.document import BlockType, Document


class MarkdownWriter:
    """Renders a Document model to a .md file."""

    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images

    def write(self, doc: Document, output_path: str) -> None:
        lines: list[str] = []

        # front matter for metadata
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
        # I²C glyph often lost in PDF text extraction → "## 2C" → "## I2C"
        text = text.replace("## 2C", "## I2C")
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
