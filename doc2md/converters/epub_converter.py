from __future__ import annotations

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".epub")
def convert_epub(path: str) -> Document:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        raise ImportError("EbookLib is required for .epub files: pip install EbookLib")

    book = epub.read_epub(path)
    doc = Document(metadata={"source": path, "title": str(book.get_metadata("DC", "title"))})

    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        html = item.get_content().decode("utf-8")
        doc.blocks.append(Block(type=BlockType.RAW_TEXT, content=_html_to_text(html)))

    return doc


def _html_to_text(html: str) -> str:
    """Simple HTML-to-text extraction without BeautifulSoup dependency at this level."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n", strip=True)
    except ImportError:
        import re
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()
