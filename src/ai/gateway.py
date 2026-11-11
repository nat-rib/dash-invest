"""Gateway de LLM independente de provedor.

O LLM só interpreta fatos já calculados pelo backend. Sem `AI_BASE_URL` e
`AI_API_KEY`, nenhuma chamada externa acontece e a narrativa determinística é
usada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class ResearchError(RuntimeError):
    pass


class NarrativeGateway(Protocol):
    name: str

    def summarize(self, *, system: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class OpenAICompatibleGateway:
    """Cliente mínimo para endpoints compatíveis com OpenAI chat/completions."""

    base_url: str
    api_key: str
    model: str
    timeout: float = 30.0
    name: str = "openai-compatible"

    def summarize(self, *, system: str, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ResearchError("Falha ao consultar o gateway de IA.") from error
        text = str(content).strip()
        if not text:
            raise ResearchError("O gateway de IA retornou resposta vazia.")
        return text


def gateway_from_env() -> NarrativeGateway | None:
    base_url = os.environ.get("AI_BASE_URL", "").strip()
    api_key = os.environ.get("AI_API_KEY", "").strip()
    if not base_url or not api_key:
        return None
    return OpenAICompatibleGateway(
        base_url=base_url,
        api_key=api_key,
        model=os.environ.get("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
    )
