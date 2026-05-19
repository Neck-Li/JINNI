import csv
import io

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".csv")
def convert_csv(path: str) -> Document:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return Document(metadata={"source": path})

    doc = Document(metadata={"source": path})

    # Build markdown table
    headers = rows[0]
    col_count = len(headers)
    divider = "|" + "|".join(["---"] * col_count) + "|"
    header_line = "|" + "|".join(headers) + "|"

    md_lines = [header_line, divider]
    for row in rows[1:]:
        # pad or trim
        padded = list(row) + [""] * (col_count - len(row))
        md_lines.append("|" + "|".join(padded[:col_count]) + "|")

    doc.blocks.append(Block(type=BlockType.TABLE, content="\n".join(md_lines)))
    return doc
