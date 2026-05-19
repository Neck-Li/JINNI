import json

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".json")
@register(".jsonl")
def convert_json(path: str) -> Document:
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".jsonl"):
            data = [json.loads(line) for line in f if line.strip()]
        else:
            data = json.load(f)

    doc = Document(metadata={"source": path})
    formatted = json.dumps(data, ensure_ascii=False, indent=2)
    doc.blocks.append(Block(type=BlockType.CODE_BLOCK, content=formatted, metadata={"language": "json"}))
    return doc
