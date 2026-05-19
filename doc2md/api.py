"""FastAPI service for JINNI — document to Markdown conversion API."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import PlainTextResponse
import uvicorn

from doc2md import convert, SUPPORTED_FORMATS

app = FastAPI(
    title="JINNI API",
    description="Document to Markdown converter — 10+ formats",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "service": "JINNI",
        "version": "0.2.0",
        "formats": sorted(SUPPORTED_FORMATS),
    }


@app.get("/formats")
def list_formats():
    return {"supported": sorted(SUPPORTED_FORMATS)}


@app.post("/convert", response_class=PlainTextResponse)
async def convert_file(
    file: UploadFile = File(...),
    llm_api_key: str | None = Form(None),
    llm_model: str | None = Form(None),
    llm_api_base: str | None = Form(None),
):
    """Upload a document and receive its Markdown conversion."""
    ext = Path(file.filename).suffix.lower() if file.filename else ".tmp"
    if ext not in SUPPORTED_FORMATS:
        return PlainTextResponse(
            f"Unsupported format: {ext}\nSupported: {', '.join(SUPPORTED_FORMATS)}",
            status_code=400,
        )

    tmp_dir = Path(tempfile.mkdtemp("jinni"))
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"

    try:
        content = await file.read()
        tmp_path.write_bytes(content)

        llm_config = None
        if llm_api_key:
            llm_config = {"api_key": llm_api_key}
            if llm_model:
                llm_config["model"] = llm_model
            if llm_api_base:
                llm_config["api_base"] = llm_api_base

        out_path = convert(str(tmp_path), output_dir=str(tmp_dir), llm_config=llm_config)
        md_content = Path(out_path).read_text(encoding="utf-8")

        return PlainTextResponse(md_content)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    """Run the API server."""
    uvicorn.run("doc2md.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
