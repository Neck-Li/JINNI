from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".rtf")
def convert_rtf(path: str) -> Document:
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        raise ImportError("striprtf is required for .rtf files: pip install striprtf")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = rtf_to_text(f.read())

    doc = Document(metadata={"source": path})
    blocks = _split_text_into_blocks(text)
    doc.blocks.extend(blocks)
    return doc


def _split_text_into_blocks(text: str) -> list[Block]:
    blocks = []
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = para.split("\n")
        first_line = lines[0].strip()

        # detect heading patterns
        if first_line.isupper() and len(first_line) < 100 and len(lines) == 1:
            blocks.append(Block(type=BlockType.HEADING, level=2, content=first_line))
        elif first_line.startswith("#"):
            level = len(first_line) - len(first_line.lstrip("#"))
            level = min(max(level, 1), 6)
            content = first_line.lstrip("#").strip()
            blocks.append(Block(type=BlockType.HEADING, level=level, content=content))
        else:
            content = "\n".join(lines)
            blocks.append(Block(type=BlockType.PARAGRAPH, content=content))

    return blocks
