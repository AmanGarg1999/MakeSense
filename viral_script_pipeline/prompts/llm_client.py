"""LLM client wrapper for script generation."""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM call."""
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class LLMClient:
    """Wrapper for LLM API calls."""
    
    def __init__(
        self,
        model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        provider: str = "nvidia",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        self.model = model
        self.provider = provider
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    def _get_client(self):
        """Lazy initialize the appropriate client."""
        if self._client is not None:
            return self._client
        
        if self.provider == "nvidia":
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or "https://integrate.api.nvidia.com/v1"
            )
        elif self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        else:
            # Default to OpenAI-compatible
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate a response from the LLM."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            if self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            else:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                text = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            
            return LLMResponse(
                text=text,
                model=self.model,
                usage=usage,
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")
    
    async def agenerate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Async version of generate."""
        # For now, just call sync version
        # Can be expanded with async clients later
        return self.generate(prompt, system_prompt)