from __future__ import annotations

import os
import unicodedata

from doc2md.converters import register
from doc2md.models.document import Block, BlockType, Document


@register(".pdf")
def convert_pdf(path: str) -> Document:
    doc = Document(metadata={"source": path})

    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF is required for .pdf files: pip install PyMuPDF")

    pdf = fitz.open(path)
    doc.metadata["pages"] = len(pdf)

    valid_tables, table_bboxes = _extract_tables(path)

    for page_num in range(len(pdf)):
        page = pdf[page_num]

        page_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        page_blocks = _reorder_by_columns(page_blocks, page.rect.width)

        # extract images
        for img_info in page.get_images(full=True):
            try:
                xref = img_info[0]
                base_image = pdf.extract_image(xref)
                img_data = base_image["image"]
                img_markdown = _pdf_img_to_markdown(img_data, os.path.dirname(path), len(doc.blocks))
                doc.blocks.append(Block(type=BlockType.IMAGE, content=img_markdown))
            except Exception:
                pass

        # collect text blocks for this page
        text_blocks_on_page = []

        for b in page_blocks:
            if b["type"] == 0:  # text block
                bbox = b["bbox"]

                # skip text inside valid table regions to avoid duplication
                if _in_table_region(bbox, table_bboxes.get(page_num, [])):
                    continue

                text = ""
                max_font_size = 0
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                        max_font_size = max(max_font_size, span.get("size", 0))
                    text += "\n"
                text = text.strip()

                if text:
                    text_blocks_on_page.append({
                        "text": text,
                        "y0": bbox[1],
                        "x0": bbox[0],
                        "font_size": max_font_size,
                    })

        _classify_and_add_blocks(text_blocks_on_page, doc)

        # add valid tables (from pdfplumber)
        for tbl_md in valid_tables.get(page_num, []):
            doc.blocks.append(Block(type=BlockType.TABLE, content=tbl_md))

    pdf.close()
    return doc


# ── Table extraction (pdfplumber) ────────────────────────────────────


def _extract_tables(path: str):
    """Extract tables from PDF using pdfplumber.

    Returns:
        valid_tables: {page_num: [md_string]} — structurally sound tables
        table_bboxes: {page_num: [(x0,y0,x1,y1)]} — regions to skip in text extraction
    """
    valid_tables: dict[int, list[str]] = {}
    table_bboxes: dict[int, list[tuple[float, float, float, float]]] = {}

    try:
        import pdfplumber
    except ImportError:
        return valid_tables, table_bboxes

    try:
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_area = page.width * page.height

                for table in page.find_tables():
                    bbox = table.bbox  # (x0, y0, x1, y1)
                    data = table.extract()

                    # sanity check: reject bboxes covering most of the page
                    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    if bbox_area > page_area * 0.8:
                        continue

                    md = _plumber_table_to_md(data)
                    if md and _is_valid_table(data):
                        valid_tables.setdefault(page_num, []).append(md)
                        # Only skip PyMuPDF text for valid tables (avoid duplication)
                        table_bboxes.setdefault(page_num, []).append(bbox)
    except Exception:
        pass

    return valid_tables, table_bboxes


def _is_valid_table(tbl_data: list[list]) -> bool:
    """Check if pdfplumber table is structurally sound vs. misidentified text layout.

    Uses conservative heuristics: prefers keeping a questionable table over
    dropping a real one. Only filters out the most egregious misdetections.
    """
    if not tbl_data or len(tbl_data) < 2:
        return False

    cols = max(len(r) for r in tbl_data) if tbl_data else 0
    if cols < 2:
        return False

    rows = len(tbl_data)
    total_cells = rows * cols

    # --- Heuristic 1: too many columns for slide/note content ---
    # Real tables rarely exceed 10 columns in slide/normal docs.
    if cols > 12:
        return False

    # --- Heuristic 2: excessive emptiness ---
    empty_cells = sum(1 for row in tbl_data for cell in row if not cell or not cell.strip())
    if empty_cells / total_cells > 0.7:
        return False

    # --- Heuristic 3: cells are too short on average ---
    # Pdfplumber misdetection: each word/punctuation becomes its own cell.
    # Exception: financial tables with numbers (each number is 1 "word").
    meaningful = []
    numeric_count = 0
    for row in tbl_data:
        for cell in row:
            if cell and cell.strip():
                text = cell.strip()
                if not all(c in '，。,．；：、（）！？""''【】《》—…·～＠＃％＆＋＝｀｜' for c in text):
                    meaningful.append(text)
                    if any(c.isdigit() for c in text):
                        numeric_count += 1

    if not meaningful:
        return False

    # If most cells contain digits -> financial table, skip word count
    if numeric_count / len(meaningful) < 0.5:
        avg_words = sum(len(c.split()) for c in meaningful) / len(meaningful)
        if avg_words < 2:
            return False

    # --- Heuristic 4: too many rows with data only in column 1 ---
    # Hierarchical financial tables often have merged cells that pdfplumber
    # can't handle, resulting in rows where all data spills into column 1.
    first_col_only = 0
    for row in tbl_data:
        padded = row + [""] * (cols - len(row))
        # Check if non-first columns are ALL empty
        rest_empty = all(
            not padded[c] or not str(padded[c]).strip()
            for c in range(1, cols)
        )
        if rest_empty and padded[0] and str(padded[0]).strip():
            first_col_only += 1

    if cols <= 8 and first_col_only / rows >= 0.8:
        return False

    return True


def _plumber_table_to_md(tbl: list) -> str:
    rows = []
    for row in tbl:
        cleaned = [(cell or "").replace("\n", " ") for cell in row]
        rows.append(cleaned)

    if not rows:
        return ""

    col_count = len(rows[0])

    # compute column widths
    col_widths = [0] * col_count
    for row in rows:
        padded = row + [""] * (col_count - len(row))
        for c in range(col_count):
            col_widths[c] = max(col_widths[c], len(padded[c]))

    # pad every cell
    def pad(text: str, width: int) -> str:
        return " " + text + " " * (width - len(text) + 1)

    lines = ["|" + "|".join(pad(rows[0][c], col_widths[c]) for c in range(col_count)) + "|"]
    lines.append("|" + "|".join(" " + "-" * col_widths[c] + " " for c in range(col_count)) + "|")
    for row in rows[1:]:
        padded = row + [""] * (col_count - len(row))
        lines.append("|" + "|".join(pad(padded[c], col_widths[c]) for c in range(col_count)) + "|")

    return "\n".join(lines)


def _in_table_region(bbox, table_bboxes: list[tuple]) -> bool:
    """Check if a text block overlaps with a detected table region."""
    if not table_bboxes:
        return False
    for tbl_bbox in table_bboxes:
        if (
            bbox[0] < tbl_bbox[2]
            and bbox[2] > tbl_bbox[0]
            and bbox[1] < tbl_bbox[3]
            and bbox[3] > tbl_bbox[1]
        ):
            return True
    return False


# ── Layout analysis ────────────────────────────────────────────────


def _reorder_by_columns(blocks: list[dict], page_width: float) -> list[dict]:
    """Detect multi-column layout via x-center clustering.
    Falls back to (y,x) sort for single-column. Uses 8% gap threshold
    with minimum 5 blocks per column guard.
    """
    if len(blocks) < 4:
        return sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

    x_centers = []
    for b in blocks:
        if b["type"] == 0:
            x_centers.append((b["bbox"][0] + b["bbox"][2]) / 2)

    if len(x_centers) < 4:
        return sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

    sorted_x = sorted(x_centers)
    min_gap = page_width * 0.08

    # Find all gaps >= threshold, pick the best column boundaries
    candidates = []
    for i in range(len(sorted_x) - 1):
        gap = sorted_x[i + 1] - sorted_x[i]
        if gap >= min_gap:
            boundary = (sorted_x[i] + sorted_x[i + 1]) / 2
            left = sum(1 for cx in x_centers if cx < boundary)
            right = sum(1 for cx in x_centers if cx > boundary)
            if left >= 5 and right >= 5:
                candidates.append((gap, boundary))

    if not candidates:
        return sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

    # Sort by gap size descending, take the biggest valid split
    candidates.sort(key=lambda x: -x[0])
    boundaries = [b for _, b in candidates[:2]]  # max 3 columns

    def column_sort_key(b):
        cx = (b["bbox"][0] + b["bbox"][2]) / 2
        col = sum(1 for g in boundaries if cx > g)
        return (col, b["bbox"][1], cx)

    return sorted(blocks, key=column_sort_key)

    return sorted(blocks, key=column_sort_key)


# ── Classification ───────────────────────────────────────────────────


def _classify_and_add_blocks(text_blocks: list[dict], doc: Document) -> None:
    """Classify text blocks as headings, lists or paragraphs, with reflow + cross-block merge."""
    if not text_blocks:
        return

    all_sizes = [b["font_size"] for b in text_blocks if b["font_size"] > 0]
    avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 12

    # First pass: reflow + classify
    page_blocks: list[Block] = []
    for tb in text_blocks:
        raw_text = tb["text"]
        font_size = tb["font_size"]

        text = _reflow_text(raw_text)
        text = text.strip()
        if not text:
            continue

        # List item detection
        if _is_list_item(text):
            page_blocks.append(Block(type=BlockType.LIST_ITEM, level=1, content=text))
            continue

        # Heading detection
        is_large = font_size > avg_size * 1.2
        is_short = len(text) < 100
        is_bold_like = text.isupper() and len(text) > 3

        if is_large and is_short:
            text = _validate_heading(text)
            if text is None:
                page_blocks.append(Block(type=BlockType.PARAGRAPH, content=raw_text.strip()))
                continue
            level = 1 if font_size > avg_size * 1.5 else 2
            page_blocks.append(Block(type=BlockType.HEADING, level=level, content=text))
        elif is_bold_like and is_short:
            text_v = _validate_heading(text)
            if text_v is None:
                page_blocks.append(Block(type=BlockType.PARAGRAPH, content=text))
            else:
                page_blocks.append(Block(type=BlockType.HEADING, level=2, content=text_v))
        else:
            page_blocks.append(Block(type=BlockType.PARAGRAPH, content=text))

    # Second pass: merge adjacent PARAGRAPH blocks split across PyMuPDF blocks
    page_blocks = _merge_split_paragraphs(page_blocks)

    for b in page_blocks:
        doc.blocks.append(b)


# ── List detection ──────────────────────────────────────────────────

_LIST_RE = None


def _is_list_item(text: str) -> bool:
    """Check if text looks like a list item (numbered, bullet, lettered)."""
    import re
    global _LIST_RE
    if _LIST_RE is None:
        _LIST_RE = re.compile(
            r'^'
            r'(?:'
            r'[（(]\d+[）)]'     # Chinese: （1） (1)
            r'|\d+[、.]'         # Digit: 1、 1.
            r'|[•·\-*]\s'        # Bullet: • - *
            r"|[a-zA-Z][.)]\s"   # Letter: a) b.
            r')'
        )
    return bool(_LIST_RE.match(text))


# ── Heading validation ──────────────────────────────────────────────

def _validate_heading(text: str) -> str | None:
    """Return text if it looks like a valid heading, None to downgrade."""
    if len(text) >= 5:
        return text
    has_cjk = any(_is_cjk(c) for c in text)
    has_alpha = any(c.isalpha() for c in text)
    if not has_cjk and not has_alpha:
        return None
    if not has_cjk and has_alpha and len(text) <= 3:
        return None
    return text


# ── Cross-block merge ───────────────────────────────────────────────

def _merge_split_paragraphs(blocks: list[Block]) -> list[Block]:
    """Merge adjacent PARAGRAPH blocks that PyMuPDF split.

    Handles cases like "A" + "temperature sensor" → "A temperature sensor"
    and Chinese fragments like "团队合" + "心价值观" → "团队合作价值观".
    """
    if not blocks:
        return blocks

    merged: list[Block] = [blocks[0]]
    for b in blocks[1:]:
        prev = merged[-1]

        if (
            prev.type in (BlockType.PARAGRAPH, BlockType.HEADING)
            and b.type in (BlockType.PARAGRAPH, BlockType.HEADING)
            and prev.content
            and b.content
        ):
            p = prev.content
            n = b.content

            # Don't merge two headings (e.g. page number + next TOC entry)
            if prev.type == BlockType.HEADING and b.type == BlockType.HEADING:
                merged.append(b)
                continue

            should_merge = False
            # Very short line ending with letter (like "A" or "or")
            if len(p) <= 3 and p[-1].isalpha():
                should_merge = True
            # English: prev ends with lowercase, next starts with lowercase
            elif p[-1].islower() and n[0].islower():
                should_merge = True
            # English: prev ends with digit, next starts with lowercase
            elif p[-1].isdigit() and n[0].islower():
                should_merge = True
            # English: prev ends with open paren
            elif p[-1] in "([" and n:
                should_merge = True
            # CJK: both contain CJK, prev doesn't end in sentence punctuation
            elif (
                _has_cjk(p)
                and _has_cjk(n)
                and p[-1] not in "。！？）；"
            ):
                should_merge = True

            if should_merge:
                spacer = " " if n[0].isalpha() else ""
                prev.content = p + spacer + n
                prev.type = BlockType.PARAGRAPH  # demote heading to paragraph after merge

        merged.append(b)

    return merged


def _has_cjk(text: str) -> bool:
    """Check if text contains at least one CJK character."""
    return any(_is_cjk(c) for c in text)


def _is_cjk(ch: str) -> bool:
    """Check if a character belongs to CJK / Chinese / Japanese / Korean."""
    try:
        cat = unicodedata.name(ch, "")
        return bool("CJK" in cat or "HIRAGANA" in cat or "KATAKANA" in cat)
    except ValueError:
        return False


def _reflow_text(text: str) -> str:
    """Merge lines broken by PDF word-splitting into flowing text.

    Handles:
    - Each-word-on-its-own-line: "An\\nembedded\\nsystem" → "An embedded system"
    - Hyphenation: "unrelat-\\ned" → "unrelated"
    - List continuations: prev line ends with comma/semicolon
    - CJK split: "这\\n是\\n一\\n个" → "这是一个" (conservative)
    """
    lines = text.split("\n")
    if len(lines) <= 1:
        return text

    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
            continue

        if not result:
            result.append(stripped)
            continue

        prev = result[-1]

        # Hyphenation: "unrelat-" + "ed" → "unrelated"
        if prev.endswith("-") and stripped[0].islower():
            result[-1] = prev[:-1] + stripped
        # Line continuation: prev ends with lowercase, curr starts with lowercase
        elif prev and prev[-1].islower() and stripped[0].islower():
            result[-1] = prev + " " + stripped
        # Continuation after comma/semicolon/colon
        elif prev and prev[-1] in ",;:" and stripped[0].islower():
            result[-1] = prev + " " + stripped
        # Very short previous line ending with letter (like "A" or "I")
        elif prev and len(prev) <= 3 and prev[-1].isalpha() and stripped[0].isalpha():
            result[-1] = prev + " " + stripped
        # CJK merge: at least one side is short → likely a page-break split
        elif (
            prev
            and _is_cjk(prev[-1])
            and _is_cjk(stripped[0])
            
            and prev[-1] not in "。！？）；】》〕"
            and stripped[0] not in "（(【《〔①②③④⑤⑥⑦⑧⑨⑩第"
        ):
            result[-1] = prev + stripped
        else:
            result.append(stripped)

    return "\n".join(result)


# ── Image extraction ─────────────────────────────────────────────────


def _pdf_img_to_markdown(img_data: bytes, output_dir: str, index: int) -> str:
    """Save PDF image and return markdown string."""
    from doc2md.utils.image_handler import save_image

    alt = f"pdf-image-{index}"
    return save_image(img_data, output_dir, alt_text=alt, index=index)
