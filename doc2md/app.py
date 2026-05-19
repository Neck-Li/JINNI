#!/usr/bin/env python3
"""Gradio web interface for doc2md — drag-and-drop file conversion."""

from __future__ import annotations

import os
import shutil
import tempfile
import traceback
import uuid
from pathlib import Path

import gradio as gr

from doc2md import convert, SUPPORTED_FORMATS
from doc2md.llm_presets import get_preset, preset_choices

# Temp directory for output files that persists across Gradio requests
_OUTPUT_DIR = Path(tempfile.gettempdir()) / "doc2md_outputs"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def convert_file(file_path: str, use_llm: bool, llm_api_key: str, llm_model: str, llm_api_base: str) -> tuple[str, str | None, str | None]:
    """Convert a single file and return (preview, full_content, output_file_path)."""
    if not file_path:
        return "Please upload a file.", None, None

    llm_config = None
    if use_llm and llm_api_key:
        llm_config = {
            "api_key": llm_api_key,
            "model": llm_model or "gpt-4o",
        }
        if llm_api_base:
            llm_config["api_base"] = llm_api_base

    try:
        ext = Path(file_path).suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            return (
                f"Unsupported format: `{ext}`\n\nSupported: `{'`, `'.join(SUPPORTED_FORMATS)}`",
                None,
                None,
            )

        # Convert to a persistent temp location
        out_dir = _OUTPUT_DIR / uuid.uuid4().hex
        out_dir.mkdir(parents=True)
        out_path = convert(file_path, output_dir=str(out_dir), llm_config=llm_config)

        # Read result
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()

        preview = content if len(content) < 50000 else content[:50000] + "\n\n... (truncated)"
        return preview, content, out_path

    except Exception as e:
        tb = traceback.format_exc()
        return f"## Error\n\n```\n{e}\n```\n\n<details><summary>Traceback</summary>\n\n```\n{tb}\n```\n</details>", None, None


def _on_provider_change(provider_key: str):
    """Update LLM fields when provider preset is selected."""
    if not provider_key:
        return (
            gr.update(value="", placeholder="sk-... or provider key", visible=True),
            gr.update(choices=[], value="", visible=True),
            gr.update(value="", placeholder="https://api.openai.com/v1", visible=True),
        )
    preset = get_preset(provider_key)
    if preset is None:
        return (
            gr.update(value="", visible=True),
            gr.update(choices=[], value="", visible=True),
            gr.update(value="", visible=True),
        )
    return (
        gr.update(value="", placeholder=preset.key_hint, visible=preset.needs_key),
        gr.update(choices=preset.models, value=preset.default_model, visible=True),
        gr.update(value=preset.api_base, visible=True),
    )


def batch_convert(files: list[str], use_llm: bool, llm_api_key: str, llm_model: str, llm_api_base: str) -> str:
    """Convert multiple files."""
    if not files:
        return "Please upload files."

    results = []
    for f in files:
        name = Path(f).name
        try:
            preview, _, _ = convert_file(f, use_llm, llm_api_key, llm_model, llm_api_base)
            preview = preview[:200] + "..." if len(preview) > 200 else preview
            results.append(f"## {name}\n\n{preview}\n\n---\n")
        except Exception as e:
            results.append(f"## {name}\n\nError: {e}\n\n---\n")

    return "\n".join(results)


def create_ui():
    with gr.Blocks(title="doc2md - Document to Markdown Converter") as demo:
        gr.Markdown(
            "# 📄 doc2md\n\n"
            "Drag and drop a document to convert it to Markdown. "
            f"Supports: {', '.join(SUPPORTED_FORMATS)}"
        )

        with gr.Tab("Single File"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="Upload Document",
                        file_types=list(SUPPORTED_FORMATS),
                    )
                    with gr.Accordion("LLM Refinement (optional)", open=False):
                        use_llm = gr.Checkbox(label="Enable LLM refinement", value=False)
                        llm_provider = gr.Dropdown(
                            label="Provider Preset",
                            choices=preset_choices(),
                            value="",
                            allow_custom_value=False,
                        )
                        llm_api_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="sk-... or provider key",
                        )
                        llm_model = gr.Dropdown(
                            label="Model",
                            choices=[],
                            allow_custom_value=True,
                            value="",
                        )
                        llm_api_base = gr.Textbox(
                            label="API Base URL",
                            placeholder="https://api.openai.com/v1",
                        )

                        llm_provider.change(
                            fn=_on_provider_change,
                            inputs=[llm_provider],
                            outputs=[llm_api_key, llm_model, llm_api_base],
                        )

                    convert_btn = gr.Button("Convert", variant="primary")

                with gr.Column(scale=1):
                    output_md = gr.Markdown(label="Preview")
                    with gr.Accordion("Raw Markdown (click to copy)", open=False):
                        output_raw = gr.Textbox(
                            label="",
                            buttons=["copy"],
                            lines=10,
                        )
                    download_file = gr.File(label="Download Markdown")

            convert_btn.click(
                fn=convert_file,
                inputs=[file_input, use_llm, llm_api_key, llm_model, llm_api_base],
                outputs=[output_md, output_raw, download_file],
            )

        with gr.Tab("Batch Convert"):
            with gr.Row():
                with gr.Column(scale=1):
                    batch_files = gr.File(
                        label="Upload Files",
                        file_count="multiple",
                        file_types=list(SUPPORTED_FORMATS),
                    )
                    with gr.Accordion("LLM Refinement (optional)", open=False):
                        batch_use_llm = gr.Checkbox(label="Enable LLM refinement", value=False)
                        batch_llm_provider = gr.Dropdown(
                            label="Provider Preset",
                            choices=preset_choices(),
                            value="",
                            allow_custom_value=False,
                        )
                        batch_llm_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="sk-... or provider key",
                        )
                        batch_llm_model = gr.Dropdown(
                            label="Model",
                            choices=[],
                            allow_custom_value=True,
                            value="",
                        )
                        batch_llm_base = gr.Textbox(
                            label="API Base URL",
                            placeholder="https://api.openai.com/v1",
                        )

                        batch_llm_provider.change(
                            fn=_on_provider_change,
                            inputs=[batch_llm_provider],
                            outputs=[batch_llm_key, batch_llm_model, batch_llm_base],
                        )
                    batch_btn = gr.Button("Convert All", variant="primary")

                with gr.Column(scale=1):
                    batch_output = gr.Markdown(label="Results")

            batch_btn.click(
                fn=batch_convert,
                inputs=[batch_files, batch_use_llm, batch_llm_key, batch_llm_model, batch_llm_base],
                outputs=[batch_output],
            )

        gr.Markdown("---\nBuilt with Gradio | Powered by doc2md")

    return demo


def _needs_ssr_workaround() -> bool:
    """Check if Gradio SSR health check needs disabling (Windows + Gradio >= 6)."""
    import sys
    if not sys.platform.startswith("win"):
        return False
    try:
        import gradio as gr
        major = int(gr.__version__.split(".")[0])
        return major >= 6
    except Exception:
        return False


def main():
    demo = create_ui()
    demo.queue(default_concurrency_limit=5)
    kwargs = dict(show_error=True, allowed_paths=[str(_OUTPUT_DIR)])
    if _needs_ssr_workaround():
        kwargs["ssr_mode"] = False
    demo.launch(**kwargs)


if __name__ == "__main__":
    main()
