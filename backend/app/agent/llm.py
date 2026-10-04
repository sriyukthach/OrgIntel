"""
LLM Provider Abstraction
Provides structured text processing, classification, and summary synthesis.
Gracefully handles missing keys and operates in offline/mock mode deterministically.
"""

import json
from typing import Optional, Dict, Any, List
from backend.app.config import settings


class LLMClient:
    """Abstract client for LLM providers (Groq, OpenAI, Mock)."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY

    async def extract_structured_json(
        self, system_prompt: str, user_content: str, schema_dict: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured JSON payload using the configured LLM provider.
        Falls back to rule-based parsing if no API key or mock provider.
        """
        if self.provider == "mock" or not self.api_key:
            return self._mock_extraction(user_content)

        if self.provider == "groq":
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=self.api_key)
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt + "\nRespond strictly in valid JSON."},
                        {"role": "user", "content": user_content[:4000]},
                    ],
                    response_format={"type": "json_object"},
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                text = response.choices[0].message.content
                return json.loads(text)
            except Exception:
                return self._mock_extraction(user_content)

        return self._mock_extraction(user_content)

    def _mock_extraction(self, text: str) -> Dict[str, Any]:
        """Deterministic rule-based fallback when LLM is unavailable or offline."""
        return {
            "summary": text[:250].strip() if text else "",
            "extracted_entities": [],
            "status": "deterministic_fallback",
        }
