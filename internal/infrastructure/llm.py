import os
import httpx
from typing import Optional, Dict, List

class LLMClient:
    """Infrastructure adapter for interacting with DeepSeek/Qwen via OpenRouter format."""
    def __init__(self, api_key: str = None, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url
        self._client = httpx.Client(timeout=120.0)
        self._async_client = httpx.AsyncClient(timeout=120.0)

    def generate_response(self, system_prompt: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None, model: str = "qwen/qwen-2.5-72b-instruct") -> str:
        """Call LLM API and return standard text output. Default model is a fallback."""
        if not self.api_key:
            return "Error: API Key not set."

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": user_prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages
        }
        
        try:
            response = self._client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"

    async def get_response_async(self, system_prompt: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None, model: str = "qwen/qwen-2.5-72b-instruct") -> str:
        """Async version of generate_response."""
        if not self.api_key:
            return "Error: API Key not set."

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": user_prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages
        }
        
        try:
            response = await self._async_client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
        except Exception as e:
            return f"Error communicating with LLM (async): {str(e)}"
