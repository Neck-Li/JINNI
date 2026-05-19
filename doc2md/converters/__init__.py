"""Format converter registry.

Each converter module registers itself via the @register decorator.
"""

from doc2md.models.document import Document

_ext_to_converter = {}
SUPPORTED_FORMATS: list[str] = []


def register(*extensions: str):
    """Decorator that registers a converter function for the given extensions."""

    def decorator(func):
        for ext in extensions:
            _ext_to_converter[ext.lower()] = func
        return func

    return decorator


def get_converter(ext: str):
    """Look up a converter by file extension."""
    ext = ext.lower()
    if ext not in _ext_to_converter:
        msg = f"Unsupported format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        raise ValueError(msg)
    return _ext_to_converter[ext]


# Import converters so they register themselves
from doc2md.converters import (  # noqa: F811, E402
    txt_converter,
    md_converter,
    csv_converter,
    json_converter,
    docx_converter,
    pdf_converter,
    html_converter,
    rtf_converter,
    epub_converter,
    pptx_converter,
)

SUPPORTED_FORMATS[:] = sorted(_ext_to_converter.keys())
