"""Ollama client wrapper."""

import json
import logging

import ollama as ollama_lib

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper around the Ollama Python client."""

    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str | None = "json",
    ) -> str:
        """Send a query to the Ollama model.

        Args:
            system_prompt: System prompt defining the LLM's role.
            user_prompt: User prompt with the specific data.
            response_format: Set to "json" for JSON output mode.

        Returns:
            The model's response text.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }
        if response_format == "json":
            kwargs["format"] = "json"

        try:
            response = ollama_lib.chat(**kwargs)
            content = response["message"]["content"]
            logger.debug("LLM response: %s", content[:200])
            return content
        except Exception as e:
            logger.error("Ollama query failed: %s", e)
            raise

    def query_json(
        self, system_prompt: str, user_prompt: str
    ) -> dict | None:
        """Send a query and parse the JSON response.

        Returns:
            Parsed JSON dict, or None if parsing fails.
        """
        raw = self.query(system_prompt, user_prompt, response_format="json")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM JSON response: %s", e)
            logger.debug("Raw response: %s", raw)
            return None

    def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            response = ollama_lib.list()
            return [m.model for m in response.models]
        except Exception as e:
            logger.error("Failed to list Ollama models: %s", e)
            raise

    def check_model(self) -> bool:
        """Check if the configured model is available."""
        try:
            models = self.list_models()
            # Check if model name matches (with or without :latest tag)
            for m in models:
                if m == self.model or m.startswith(self.model + ":"):
                    return True
            return False
        except Exception:
            return False
