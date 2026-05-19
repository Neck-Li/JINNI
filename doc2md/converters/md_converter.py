import re

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".md", ".markdown")
def convert_md(path: str) -> Document:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    doc = Document(metadata={"source": path})
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
            doc.blocks.append(Block(type=BlockType.HORIZONTAL_RULE, content=""))
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$", line)
        if m:
            level = len(m.group(1))
            content = m.group(2)
            doc.blocks.append(
                Block(type=BlockType.HEADING, level=level, content=content)
            )
            i += 1
            continue

        # fenced code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            doc.blocks.append(
                Block(
                    type=BlockType.CODE_BLOCK,
                    content="\n".join(code),
                    metadata={"language": lang},
                )
            )
            continue

        # blockquote
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").strip())
                i += 1
            doc.blocks.append(
                Block(type=BlockType.BLOCKQUOTE, content="\n".join(quote))
            )
            continue

        # table
        if "|" in line and i + 1 < len(lines) and "---" in lines[i + 1]:
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            md_table = "\n".join(table_lines)
            doc.blocks.append(Block(type=BlockType.TABLE, content=md_table))
            continue

        # image
        img_m = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line.strip())
        if img_m:
            doc.blocks.append(
                Block(
                    type=BlockType.IMAGE,
                    content=line.strip(),
                    metadata={"alt": img_m.group(1), "src": img_m.group(2)},
                )
            )
            i += 1
            continue

        # list item
        if re.match(r"^(\s*)[-*+]\s", line) or re.match(r"^(\s*)\d+[.)]\s", line):
            items = []
            while i < len(lines):
                if re.match(r"^(\s*)[-*+]\s", lines[i]) or re.match(r"^(\s*)\d+[.)]\s", lines[i]):
                    items.append(lines[i].strip())
                    i += 1
                elif i + 1 < len(lines) and lines[i].strip() == "" and re.match(r"^(\s*)[-*+]\s", lines[i + 1]):
                    i += 1  # skip blank between items
                else:
                    break
            for item in items:
                content = re.sub(r"^[-*+]\s+|^\d+[.)]\s+", "", item)
                doc.blocks.append(
                    Block(type=BlockType.LIST_ITEM, level=1, content=content)
                )
            continue

        # paragraph (skip empty)
        if line.strip():
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip():
                para.append(lines[i])
                i += 1
            doc.blocks.append(
                Block(type=BlockType.PARAGRAPH, content="\n".join(para))
            )
            continue

        i += 1

    return doc
