from __future__ import annotations

import json
from pathlib import Path

import click

from doc2md import convert, SUPPORTED_FORMATS
from doc2md.llm_presets import get_preset, preset_choices


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("-o", "--output", "output_path", help="Output .md file path")
@click.option("--output-dir", help="Output directory (default: same as input)")
@click.option("--llm-config", help='JSON string or path to JSON file with LLM config: {"api_key": "...", "model": "...", "api_base": "..."}')
@click.option("--provider", type=click.Choice([v for _, v in preset_choices() if v], case_sensitive=False), help="LLM provider preset (overrides api_base, sets default model)")
@click.option("--no-images", is_flag=True, help="Skip image extraction")
@click.option("--recursive", is_flag=True, help="Process directory recursively")
def main(input_path, output_path, output_dir, llm_config, provider, no_images, recursive):
    """Convert documents to Markdown.

    INPUT_PATH can be a file or a directory. Supported formats: all common document formats.
    """
    llm_conf = _resolve_llm_config(llm_config, provider)
    input_path = Path(input_path)
    extract_images = not no_images

    if input_path.is_dir():
        files = list(input_path.rglob("*") if recursive else input_path.glob("*"))
        supported = []
        for f in files:
            if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
                supported.append(f)

        if not supported:
            click.echo(f"No supported files found in {input_path}", err=True)
            click.echo(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}", err=True)
            raise SystemExit(1)

        click.echo(f"Found {len(supported)} file(s) to convert...")
        for f in supported:
            try:
                out = convert(
                    str(f),
                    output_dir=output_dir or str(input_path),
                    llm_config=llm_conf,
                    extract_images=extract_images,
                )
                click.echo(f"  OK {f.name} -> {out}")
            except Exception as e:
                click.echo(f"  FAIL {f.name}: {e}", err=True)
    else:
        try:
            out = convert(
                str(input_path),
                output_path=output_path,
                output_dir=output_dir,
                llm_config=llm_conf,
                extract_images=extract_images,
            )
            click.echo(f"Converted: {out}")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)


def _parse_llm_config(config_str: str) -> dict:
    """Parse LLM config from JSON string or file path."""
    path = Path(config_str)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return json.loads(config_str)


def _resolve_llm_config(config_str: str | None, provider: str | None) -> dict | None:
    """Resolve LLM config from --llm-config and/or --provider."""
    conf = None
    if config_str:
        conf = _parse_llm_config(config_str)

    if provider:
        preset = get_preset(provider)
        if preset:
            base = {"api_base": preset.api_base, "model": preset.default_model}
            if conf:
                # conf overrides preset defaults
                base.update(conf)
            conf = base

    return conf


if __name__ == "__main__":
    main()
