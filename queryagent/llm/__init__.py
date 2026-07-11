"""LLM backend implementations behind the ``LLMBackend`` protocol."""

from __future__ import annotations

from queryagent.config import LLMConfig
from queryagent.llm.base import LLMBackend


def make_backend(config: LLMConfig) -> LLMBackend:
    """Build the backend matching a validated llm config.

    Imports are lazy so that using one provider never requires the other's
    SDK to be importable.
    """
    if config.backend == "anthropic":
        from queryagent.llm.anthropic_backend import AnthropicBackend

        return AnthropicBackend(model=config.model)
    if config.backend == "openai_compatible":
        from queryagent.llm.openai_backend import OpenAICompatibleBackend

        # base_url presence is enforced by config validation.
        return OpenAICompatibleBackend(model=config.model, base_url=config.base_url or "")
    raise ValueError(f"unsupported llm backend: {config.backend}")
