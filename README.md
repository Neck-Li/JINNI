# doc2md

**Document to Markdown converter** — CLI + Gradio UI, supports 10+ document formats.

```bash
pip install doc2md
doc2md input.docx          # CLI
doc2md input.pdf -o output.md
python -m doc2md.app       # Gradio web UI
```

## Features

- **10 formats, 14 extensions**: `.docx` `.pdf` `.txt` `.text` `.md` `.markdown` `.csv` `.json` `.jsonl` `.html` `.htm` `.rtf` `.epub` `.pptx`
- **CLI + Gradio GUI**: both included
- **LLM refinement**: optional AI-powered segmentation (bring your own API key)
- **Free provider presets**: Groq, GitHub Models, SiliconFlow, Zhipu, OpenRouter, etc.
- **Image extraction**: extracts images from PDF, EPUB, DOCX
- **Chinese-friendly**: tested on Chinese/English mixed documents

## Quick Start

```bash
# Convert a file
doc2md document.pdf

# Specify output
doc2md document.docx -o output.md

# Batch convert directory
doc2md ./papers/ --recursive --output-dir ./output/

# Launch web interface
python -m doc2md.app
```

## Supported Formats

| Format | Extensions | Converter |
|--------|-----------|-----------|
| Word | `.docx` | python-docx |
| PDF | `.pdf` | PyMuPDF + pdfplumber |
| PowerPoint | `.pptx` | python-pptx |
| HTML | `.html` `.htm` | BeautifulSoup |
| EPUB | `.epub` | ebooklib |
| RTF | `.rtf` | striprtf |
| Plain text | `.txt` `.text` | built-in |
| Markdown | `.md` `.markdown` | built-in |
| CSV | `.csv` | built-in |
| JSON | `.json` `.jsonl` | built-in |

## License

MIT
