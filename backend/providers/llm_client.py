"""
Pluggable LLM interface supporting streaming chat and post-call data extraction.
Uses Groq OpenAI-compatible API by default with configurable model and low temperature.
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

import httpx
from pydantic import BaseModel, ValidationError

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "qwen/qwen3.8-27b"


class SessionExtraction(BaseModel):
    """Pydantic model for post-conversation extraction."""

    interest_level: Literal["high", "medium", "low", "none", "unknown"]
    loan_amount_inr: Optional[float] = None
    callback_time: Optional[str] = None
    language_used: List[str]
    outcome: Literal["interested", "not_interested", "callback", "no_answer", "unclear"]
    summary: str


class LLMClient:
    """Client for streaming dialogue generation and post-conversation extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize LLM client with credentials, model name, and endpoint."""
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self._model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self._base_url = base_url or GROQ_BASE_URL

        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not set or empty")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> AsyncIterator[str]:
        """Stream tokens from LLM completion using server-sent events."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            async with client.stream(
                "POST", f"{self._base_url}/chat/completions", headers=headers, json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw_data = line[5:].strip()
                    if raw_data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw_data)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    async def extract_session_data(
        self,
        transcript: List[Dict[str, str]],
        info_to_collect: Optional[List[Dict[str, Any]]] = None,
        success_condition: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract strictly validated SessionExtraction model from conversation transcript."""
        conversation_text = "\n".join(
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in transcript
        )

        extraction_system_prompt = (
            "You are a structured data extractor for voice calls. Return ONLY a valid JSON object matching:\n"
            "- interest_level: one of ['high', 'medium', 'low', 'none', 'unknown']\n"
            "- loan_amount_inr: number in INR (e.g. 100000) or null if not spoken. NEVER invent values.\n"
            "- callback_time: string or null if not spoken. NEVER invent values.\n"
            "- language_used: list of language codes observed (e.g. ['en-IN', 'hi-IN'])\n"
            "- outcome: one of ['interested', 'not_interested', 'callback', 'no_answer', 'unclear']\n"
            "- summary: concise 2-3 sentence English summary\n"
            "Output strictly valid JSON and nothing else. No markdown fences."
        )

        messages = [
            {"role": "system", "content": extraction_system_prompt},
            {"role": "user", "content": f"Transcript:\n{conversation_text}"},
        ]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 512,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions", headers=headers, json=payload
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.strip("`").replace("json\n", "", 1).strip()
            try:
                raw_dict = json.loads(content)
                validated = SessionExtraction.model_validate(raw_dict)
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError):
                return SessionExtraction(
                    interest_level="unknown",
                    loan_amount_inr=None,
                    callback_time=None,
                    language_used=["en-IN"],
                    outcome="unclear",
                    summary=content[:300] if content else "Extraction failed",
                ).model_dump()
