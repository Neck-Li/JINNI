"""Free LLM provider presets for doc2md.

Each preset is compatible with the OpenAI SDK format.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMPreset:
    """Configuration preset for a free LLM provider."""

    name: str
    api_base: str
    models: list[str]
    default_model: str
    needs_key: bool
    key_hint: str
    description: str = ""


PRESETS: dict[str, LLMPreset] = {
    "groq": LLMPreset(
        name="Groq (Free)",
        api_base="https://api.groq.com/openai/v1",
        models=[
            "llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
            "deepseek-r1-distill-llama-70b",
            "qwen-2.5-32b",
        ],
        default_model="llama-3.3-70b-versatile",
        needs_key=True,
        key_hint="Free key: https://console.groq.com/keys",
        description="Fastest open-source inference, 14400 req/day",
    ),
    "github": LLMPreset(
        name="GitHub Models (Free)",
        api_base="https://models.inference.ai.azure.com",
        models=[
            "gpt-4o",
            "o3-mini",
            "Llama-4-cybertron-17b-4e-instruct",
        ],
        default_model="gpt-4o",
        needs_key=True,
        key_hint="Free key: https://github.com/settings/tokens",
        description="Includes GPT-4.1, o3-mini, Llama 4 — 10-150 req/day",
    ),
    "openrouter": LLMPreset(
        name="OpenRouter (Free models)",
        api_base="https://openrouter.ai/api/v1",
        models=["free"],
        default_model="free",
        needs_key=True,
        key_hint="Free key: https://openrouter.ai/keys",
        description="Aggregates 35+ free models, unified API",
    ),
    "siliconflow": LLMPreset(
        name="SiliconFlow (Free)",
        api_base="https://api.siliconflow.cn/v1",
        models=[
            "Qwen/Qwen3-8B",
            "deepseek-ai/DeepSeek-V3",
            "THUDM/glm-4-9b-chat",
        ],
        default_model="Qwen/Qwen3-8B",
        needs_key=True,
        key_hint="Free key: https://cloud.siliconflow.cn",
        description="China-friendly, fast, 1000 RPM",
    ),
    "zhipu": LLMPreset(
        name="Zhipu GLM (Free)",
        api_base="https://open.bigmodel.cn/api/paas/v4",
        models=[
            "glm-4.7-flash",
            "glm-4.5-flash",
        ],
        default_model="glm-4.7-flash",
        needs_key=True,
        key_hint="Free key: https://open.bigmodel.cn",
        description="Zhipu free models, China-friendly, 200K context",
    ),
    "cerebras": LLMPreset(
        name="Cerebras (Free)",
        api_base="https://api.cerebras.ai/v1",
        models=[
            "llama-3.1-8b",
            "qwen3-235b",
        ],
        default_model="llama-3.1-8b",
        needs_key=True,
        key_hint="Free key: https://cloud.cerebras.ai",
        description="Extremely fast inference, 1M tokens/day free",
    ),
    "ollama": LLMPreset(
        name="Ollama (Local)",
        api_base="http://localhost:11434/v1",
        models=[],
        default_model="",
        needs_key=False,
        key_hint="No API key needed, run models locally",
        description="Run open-source models locally, fully free",
    ),
}


def get_preset(key: str) -> LLMPreset | None:
    """Look up a preset by key. Returns None if not found."""
    return PRESETS.get(key)


def preset_choices() -> list[tuple[str, str]]:
    """Return list of (label, value) pairs for Gradio dropdown."""
    return [("Custom", "")] + [(p.name, k) for k, p in PRESETS.items()]
