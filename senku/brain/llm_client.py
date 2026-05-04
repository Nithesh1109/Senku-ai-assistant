"""
Senku LLM Client
Robust Ollama API client with retry logic, timeout handling, and error recovery.
"""

import json
import time
from typing import Optional

import requests

from senku.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
    DEBUG_MODE,
)
from senku.core.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMModelError,
)


class LLMClient:
    """
    Robust Ollama API client.
    
    Features:
    - Automatic retry with exponential backoff
    - Timeout handling
    - Model availability checking
    - Response validation
    - Debug logging
    """

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self._api_url = f"{self.base_url}/api/generate"
        self._model_verified = False

    def generate(self, prompt: str, temperature: float = None,
                 max_tokens: int = None, timeout: int = None) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The full prompt to send
            temperature: Override default temperature
            max_tokens: Override default max tokens
            timeout: Override default timeout
            
        Returns:
            The generated text response
            
        Raises:
            LLMConnectionError: Cannot reach Ollama
            LLMTimeoutError: Request timed out
            LLMModelError: Model not found
        """
        temp = temperature if temperature is not None else LLM_TEMPERATURE
        tokens = max_tokens or LLM_MAX_TOKENS
        req_timeout = timeout or LLM_TIMEOUT

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": tokens,
            }
        }

        last_error = None
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                if DEBUG_MODE:
                    print(f"[LLM] Attempt {attempt + 1}, prompt length: {len(prompt)}")

                response = requests.post(
                    self._api_url,
                    json=payload,
                    timeout=req_timeout,
                )

                # Handle HTTP errors
                if response.status_code == 404:
                    raise LLMModelError(self.model)
                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict) and "response" in data:
                    result = data["response"].strip()
                    if DEBUG_MODE:
                        print(f"[LLM] Response length: {len(result)}")
                    return result

                # Unexpected response format
                return str(data)

            except requests.ConnectionError as e:
                last_error = LLMConnectionError(self.base_url, str(e))
            except requests.Timeout:
                last_error = LLMTimeoutError(req_timeout)
            except LLMModelError:
                raise  # Don't retry model errors
            except requests.RequestException as e:
                last_error = LLMConnectionError(self.base_url, str(e))

            # Exponential backoff before retry
            if attempt < LLM_MAX_RETRIES:
                wait_time = (2 ** attempt) * 0.5
                if DEBUG_MODE:
                    print(f"[LLM] Retrying in {wait_time}s...")
                time.sleep(wait_time)

        # All retries exhausted
        raise last_error

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "").split(":")[0]
                          for m in data.get("models", [])]
                return self.model in models
            return False
        except (requests.RequestException, json.JSONDecodeError):
            return False

    def check_connection(self) -> dict:
        """
        Perform a health check.
        Returns status dict with details.
        """
        result = {
            "ollama_running": False,
            "model_available": False,
            "model_name": self.model,
            "base_url": self.base_url,
            "error": None,
        }

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                result["ollama_running"] = True
                data = response.json()
                models = [m.get("name", "").split(":")[0]
                          for m in data.get("models", [])]
                result["model_available"] = self.model in models
                if not result["model_available"]:
                    result["error"] = (
                        f"Model '{self.model}' not found. "
                        f"Available: {', '.join(models) or 'none'}. "
                        f"Run: ollama pull {self.model}"
                    )
            else:
                result["error"] = f"Ollama returned status {response.status_code}"
        except requests.ConnectionError:
            result["error"] = (
                f"Cannot connect to Ollama at {self.base_url}. "
                "Run: ollama serve"
            )
        except requests.Timeout:
            result["error"] = "Connection to Ollama timed out"
        except Exception as e:
            result["error"] = str(e)

        return result
