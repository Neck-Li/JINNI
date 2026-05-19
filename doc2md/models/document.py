from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BlockType(Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"
    RAW_TEXT = "raw_text"
    UNSUPPORTED = "unsupported"


@dataclass
class Block:
    """A single content block in the document."""

    type: BlockType
    content: str
    level: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class Document:
    """Intermediate representation of a parsed document."""

    metadata: dict = field(default_factory=dict)
    blocks: list[Block] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
