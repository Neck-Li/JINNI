from __future__ import annotations

import json
import re
from pathlib import Path

from doc2md.models.document import Block, BlockType, Document


def segment_document(
    doc: Document,
    llm_config: dict | None = None,
    output_dir: str | None = None,
) -> Document:
    """Apply rule-based segmentation, then optional LLM refinement."""
    doc = _rule_based_segment(doc)

    if llm_config:
        doc = _llm_refine(doc, llm_config)

    return doc


# ── Rule-based segmentation ──────────────────────────────────────────


def _rule_based_segment(doc: Document) -> Document:
    blocks = list(doc.blocks)
    if not blocks:
        return doc

    blocks = _merge_consecutive_same_level(blocks)
    blocks = _normalize_headings(blocks)
    blocks = _split_long_paragraphs(blocks)
    blocks = _merge_short_paragraphs(blocks)

    doc.blocks = blocks
    return doc


def _merge_consecutive_same_level(blocks: list[Block]) -> list[Block]:
    """Merge consecutive paragraphs at same nesting into one block."""
    if not blocks:
        return blocks

    merged = [blocks[0]]
    for b in blocks[1:]:
        prev = merged[-1]
        # merge consecutive paragraphs (not separated by headings / tables / etc.)
        if (
            prev.type == BlockType.PARAGRAPH
            and b.type == BlockType.PARAGRAPH
        ):
            prev.content += "\n\n" + b.content
        else:
            merged.append(b)

    return merged


def _normalize_headings(blocks: list[Block]) -> list[Block]:
    """Ensure heading levels start at 1 and are sequential."""
    headings = [b for b in blocks if b.type == BlockType.HEADING]
    if not headings:
        return blocks

    min_level = min(b.level for b in headings)
    if min_level > 1:
        for b in headings:
            b.level = max(1, b.level - min_level + 1)

    return blocks


def _split_long_paragraphs(blocks: list[Block], max_chars: int = 2000) -> list[Block]:
    """Split paragraphs that are excessively long (for better LLM context fit)."""
    result = []
    for b in blocks:
        if b.type == BlockType.PARAGRAPH and len(b.content) > max_chars:
            sentences = re.split(r"(?<=[。！？.!?\n])\s*", b.content)
            chunk = ""
            for sent in sentences:
                if len(chunk) + len(sent) > max_chars and chunk:
                    result.append(Block(type=BlockType.PARAGRAPH, content=chunk.strip()))
                    chunk = sent
                else:
                    chunk += sent
            if chunk.strip():
                result.append(Block(type=BlockType.PARAGRAPH, content=chunk.strip()))
        else:
            result.append(b)
    return result


def _merge_short_paragraphs(blocks: list[Block], min_chars: int = 20) -> list[Block]:
    """Merge very short paragraphs into the previous paragraph."""
    if len(blocks) < 2:
        return blocks

    result = [blocks[0]]
    for b in blocks[1:]:
        prev = result[-1]
        if (
            b.type == BlockType.PARAGRAPH
            and prev.type == BlockType.PARAGRAPH
            and len(b.content) < min_chars
        ):
            prev.content += "\n\n" + b.content
        else:
            result.append(b)
    return result


# ── LLM-based refinement ────────────────────────────────────────────


def _llm_refine(doc: Document, config: dict) -> Document:
    """Use an LLM to refine segmentation boundaries."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Warning: openai package not installed, skipping LLM refinement")
        return doc

    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o")
    api_base = config.get("api_base", None)

    if not api_key:
        print("Warning: no api_key provided for LLM refinement, skipping")
        return doc

    client = OpenAI(api_key=api_key, base_url=api_base) if api_base else OpenAI(api_key=api_key)

    blocks = doc.blocks

    processed = []
    chunk = []
    char_count = 0
    max_chars = config.get("max_context_chars", 6000)

    for block in blocks:
        text = _block_to_text(block)
        if char_count + len(text) > max_chars and chunk:
            refined = _refine_chunk(client, model, chunk)
            processed.extend(refined)
            chunk = [block]
            char_count = len(text)
        else:
            chunk.append(block)
            char_count += len(text)

    if chunk:
        refined = _refine_chunk(client, model, chunk)
        processed.extend(refined)

    doc.blocks = processed
    return doc


def _block_to_text(block: Block) -> str:
    prefix = {
        BlockType.HEADING: "#" * block.level + " ",
        BlockType.LIST_ITEM: ("  " * (block.level - 1)) + "- ",
        BlockType.BLOCKQUOTE: "> ",
        BlockType.CODE_BLOCK: "```\n",
        BlockType.TABLE: "",
        BlockType.IMAGE: "",
        BlockType.HORIZONTAL_RULE: "",
        BlockType.PARAGRAPH: "",
        BlockType.RAW_TEXT: "",
        BlockType.UNSUPPORTED: "",
    }.get(block.type, "")
    suffix = "\n```" if block.type == BlockType.CODE_BLOCK else ""
    return prefix + block.content + suffix


REFINE_SYSTEM_PROMPT = """You are a document structure analyzer. Your task is to review document segments and improve their structure.

For each block in the document, analyze it and output a JSON array where each element has:
- "type": one of "heading", "paragraph", "list_item", "code_block", "blockquote", "table", "image", "horizontal_rule"
- "level": integer, heading level (1-6) or list indent level
- "content": the text content
- "action": "keep" or "merge_with_next" if this block should be merged with the next block

Rules:
1. If a heading-style line is misclassified, correct its type
2. If consecutive blocks are about the same topic and should be merged, mark them with "merge_with_next"
3. Ensure heading levels form a logical hierarchy
4. Keep table, image, code_block, and horizontal_rule blocks as-is
5. Output ONLY valid JSON, no other text"""


def _refine_chunk(client, model: str, blocks: list[Block]) -> list[Block]:
    """Send a chunk of blocks to the LLM for refinement."""
    blocks_json = []
    for i, b in enumerate(blocks):
        blocks_json.append({
            "index": i,
            "type": b.type.value,
            "level": b.level,
            "content": b.content[:500],  # truncate very long content per block
        })

    prompt = json.dumps(blocks_json, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        result = json.loads(raw)

        decisions = result.get("blocks", result) if isinstance(result, dict) else result

        refined = []
        merge_buffer = None

        for entry in decisions:
            if not isinstance(entry, dict):
                continue

            action = entry.get("action", "keep")
            idx = entry.get("index", len(refined))
            block_type_str = entry.get("type", "paragraph")
            level = entry.get("level", 0)
            content = entry.get("content", "")

            try:
                bt = BlockType(block_type_str)
            except ValueError:
                bt = BlockType.PARAGRAPH

            block = Block(type=bt, level=level, content=content, metadata=blocks[idx].metadata if idx < len(blocks) else {})

            if action == "merge_with_next":
                if merge_buffer is None:
                    merge_buffer = block
                else:
                    merge_buffer.content += "\n\n" + block.content
            else:
                if merge_buffer is not None:
                    refined.append(merge_buffer)
                    merge_buffer = None
                refined.append(block)

        if merge_buffer is not None:
            refined.append(merge_buffer)

        return refined if refined else blocks

    except Exception as e:
        print(f"Warning: LLM refinement failed for chunk: {e}")
        return blocks
