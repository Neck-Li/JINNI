from __future__ import annotations

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".html")
@register(".htm")
def convert_html(path: str) -> Document:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 is required for .html files: pip install beautifulsoup4")

    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    doc = Document(metadata={"source": path, "title": (soup.title.string if soup.title else "")})
    body = soup.body or soup

    for el in body.children:
        if not hasattr(el, "name") or el.name is None:
            continue

        tag = el.name
        text = el.get_text(strip=True)

        if not text and tag not in ("img", "hr", "table"):
            continue

        match tag:
            case "h1" | "h2" | "h3" | "h4" | "h5" | "h6":
                level = int(tag[1])
                doc.blocks.append(Block(type=BlockType.HEADING, level=level, content=text))

            case "p":
                doc.blocks.append(Block(type=BlockType.PARAGRAPH, content=text))

            case "blockquote":
                doc.blocks.append(Block(type=BlockType.BLOCKQUOTE, content=text))

            case "hr":
                doc.blocks.append(Block(type=BlockType.HORIZONTAL_RULE, content=""))

            case "ul" | "ol":
                items = el.find_all("li", recursive=False)
                for li in items:
                    doc.blocks.append(
                        Block(type=BlockType.LIST_ITEM, level=1, content=li.get_text(strip=True))
                    )

            case "pre":
                code = el.get_text("\n")
                lang = ""
                code_el = el.find("code")
                if code_el and code_el.get("class"):
                    cls = code_el["class"]
                    if len(cls) > 1 and cls[0].startswith("language-"):
                        lang = cls[0][9:]
                doc.blocks.append(
                    Block(type=BlockType.CODE_BLOCK, content=code.strip(), metadata={"language": lang})
                )

            case "table":
                md_table = _html_table_to_md(el)
                if md_table:
                    doc.blocks.append(Block(type=BlockType.TABLE, content=md_table))

            case "img":
                src = el.get("src", "")
                alt = el.get("alt", "")
                doc.blocks.append(Block(type=BlockType.IMAGE, content=f"![{alt}]({src})"))

            case _:
                if text:
                    doc.blocks.append(Block(type=BlockType.PARAGRAPH, content=text))

    return doc


def _html_table_to_md(table) -> str:
    rows = table.find_all("tr")
    if not rows:
        return ""

    # headers
    headers = []
    ths = rows[0].find_all("th") or rows[0].find_all("td")
    for th in ths:
        headers.append(th.get_text(strip=True))

    col_count = len(headers) if headers else len(rows[0].find_all("td"))
    if col_count == 0:
        return ""

    lines = []
    # header row
    if headers:
        lines.append("|" + "|".join(headers) + "|")
    else:
        lines.append("|" + "|".join([""] * col_count) + "|")
    # divider
    lines.append("|" + "|".join(["---"] * col_count) + "|")
    # data rows
    start = 0 if headers else 1
    for row in rows[start:]:
        cells = row.find_all("td")
        row_data = [c.get_text(strip=True) for c in cells]
        padded = row_data + [""] * (col_count - len(row_data))
        lines.append("|" + "|".join(padded[:col_count]) + "|")

    return "\n".join(lines)
