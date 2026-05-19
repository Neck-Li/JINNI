from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".txt", ".text")
def convert_txt(path: str) -> Document:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    doc = Document(metadata={"source": path})
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # empty line → paragraph break
        if not line:
            i += 1
            continue

        # horizontal rule
        if line.strip() in ("---", "***", "___"):
            doc.blocks.append(Block(type=BlockType.HORIZONTAL_RULE, content=""))
            i += 1
            continue

        # heading (markdown-style #)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            level = min(max(level, 1), 6)
            content = stripped.lstrip("#").strip()
            doc.blocks.append(Block(type=BlockType.HEADING, level=level, content=content))
            i += 1
            continue

        # heading (all-caps short line heuristic)
        clean = line.strip()
        if (
            clean.isupper()
            and len(clean) > 2
            and len(clean) < 80
            and not clean[-1].isalnum()
        ):
            doc.blocks.append(Block(type=BlockType.HEADING, level=2, content=clean))
            i += 1
            continue

        # code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            doc.blocks.append(
                Block(
                    type=BlockType.CODE_BLOCK,
                    content="\n".join(code_lines),
                    metadata={"language": lang},
                )
            )
            continue

        # blockquote
        if line.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                quote_lines.append(lines[i].lstrip("> ").strip())
                i += 1
            doc.blocks.append(
                Block(type=BlockType.BLOCKQUOTE, content="\n".join(quote_lines))
            )
            continue

        # list item
        if line.strip().startswith(("- ", "* ", "+ ")) or line.strip()[0].isdigit():
            list_lines = []
            while i < len(lines):
                l = lines[i].rstrip()
                if not l or l.strip().startswith(("- ", "* ", "+ ")) or (l.strip() and l.strip()[0].isdigit()):
                    list_lines.append(l)
                    i += 1
                else:
                    break
            for l in list_lines:
                if l:
                    marker = l.strip().split()[0]
                    content = l.strip()[len(marker):].strip()
                    doc.blocks.append(
                        Block(type=BlockType.LIST_ITEM, level=1, content=content)
                    )
            continue

        # regular paragraph
        para_lines = [line]
        i += 1
        while i < len(lines):
            l = lines[i].rstrip()
            if l and not l.startswith("#") and not l.startswith("```") and not l.startswith(">"):
                para_lines.append(l)
                i += 1
            else:
                break
        doc.blocks.append(
            Block(type=BlockType.PARAGRAPH, content="\n".join(para_lines))
        )

    return doc
