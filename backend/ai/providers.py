"""
CoreMatch — AI Provider Abstraction Layer
Configurable AI providers for the agentic pipeline.
Supports Groq, Anthropic (Claude), and OpenAI.
Provider selected per-stage via pipeline_configs.stages JSONB.
"""
import os
import json
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standardized output from any AI pipeline agent."""
    overall_score: float = 0.0
    scores_detail: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = "needs_review"   # advance | reject | needs_review
    confidence: float = 0.0
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    model_used: str = ""
    provider: str = ""
    raw_response: Dict = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: int = 0


# ──────────────────────────────────────────────────────────────
# Provider Interface
# ──────────────────────────────────────────────────────────────

class AIProvider:
    """Base class for AI providers."""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request. Returns parsed JSON response + metadata."""
        raise NotImplementedError


class GroqProvider(AIProvider):
    """Groq API provider (LLama, Mixtral, etc.)."""

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        from groq import Groq
        self._client = Groq(api_key=api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.time() - start) * 1000)

        content = response.choices[0].message.content
        tokens_used = getattr(response.usage, 'total_tokens', 0) if response.usage else 0

        return {
            "content": content,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": model,
            "provider": "groq",
        }


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.2,
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        # Anthropic uses system message separately
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        kwargs = {
            "model": model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = self._client.messages.create(**kwargs)
        latency_ms = int((time.time() - start) * 1000)

        content = response.content[0].text
        tokens_used = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0

        return {
            "content": content,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": model,
            "provider": "anthropic",
        }


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 2000,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.time() - start) * 1000)

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        return {
            "content": content,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": model,
            "provider": "openai",
        }


# ──────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────

_PROVIDERS = {
    "groq": GroqProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str) -> AIProvider:
    """Get an AI provider instance by name."""
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[name]()


def get_provider_for_stage(pipeline_config: Dict, stage: int) -> tuple:
    """Get the configured provider + model for a specific pipeline stage.

    Args:
        pipeline_config: The pipeline_configs row (with 'stages' JSONB and defaults).
        stage: Stage number (1-4).

    Returns:
        Tuple of (AIProvider instance, model_name string).
    """
    stages = pipeline_config.get("stages", [])
    stage_config = None
    for s in stages:
        if s.get("stage") == stage:
            stage_config = s
            break

    if stage_config:
        provider_name = stage_config.get("provider", pipeline_config.get("default_provider", "groq"))
        model_name = stage_config.get("model", pipeline_config.get("default_model", "llama-3.3-70b-versatile"))
    else:
        provider_name = pipeline_config.get("default_provider", "groq")
        model_name = pipeline_config.get("default_model", "llama-3.3-70b-versatile")

    provider = get_provider(provider_name)
    return provider, model_name


def parse_json_response(content: str) -> Dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    content = content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM response: %s", content[:200])
        return {}
