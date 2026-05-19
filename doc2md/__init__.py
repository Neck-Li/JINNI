from pathlib import Path

from doc2md.converters import get_converter, SUPPORTED_FORMATS
from doc2md.segmenter.segmenter import segment_document
from doc2md.writers.markdown_writer import MarkdownWriter


def convert(
    input_path: str,
    output_path: str | None = None,
    output_dir: str | None = None,
    llm_config: dict | None = None,
    extract_images: bool = True,
) -> str:
    """Convert a document to Markdown.

    Args:
        input_path: Path to input file.
        output_path: Path for output .md file. If not given, inferred from input name.
        output_dir: Directory for output and extracted images. Defaults to input file's parent.
        llm_config: Optional LLM config for segmentation refinement:
            {"api_key": "...", "model": "...", "api_base": "..."}
        extract_images: Whether to extract and save images.

    Returns:
        Path to the output .md file.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = input_path.suffix.lower()
    converter_fn = get_converter(ext)

    doc = converter_fn(str(input_path))

    doc = segment_document(doc, llm_config=llm_config, output_dir=output_dir)

    if output_dir is None:
        output_dir = str(input_path.parent)
    else:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    if output_path is None:
        stem = input_path.stem
        output_path = str(Path(output_dir) / f"{stem}.md")

    writer = MarkdownWriter(extract_images=extract_images)
    writer.write(doc, output_path)

    return output_path


__all__ = ["convert", "SUPPORTED_FORMATS"]
