from __future__ import annotations
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from rumik.config import Cfg


class BedrockClient:
    """Thin client for AWS Bedrock Converse API using bearer token auth."""

    def __init__(
        self,
        bearer_token: str | None = None,
        region: str | None = None,
        model_id: str | None = None,
    ):
        self.bearer_token = bearer_token or Cfg.AWS_BEARER_TOKEN_BEDROCK
        self.region = region or Cfg.BEDROCK_REGION
        self.model_id = model_id or Cfg.BEDROCK_MODEL_ID
        self.endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com"

        if not self.bearer_token:
            raise RuntimeError(
                "Missing AWS_BEARER_TOKEN_BEDROCK. "
                "Set it in environment or .env file."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
    )
    def converse(
        self,
        messages: list[dict],
        system: str | None = None,
        model_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        model = model_id or self.model_id
        url = f"{self.endpoint}/model/{model}/converse"

        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body: dict = {
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }

        if system:
            body["system"] = [{"text": system}]

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

    def converse_text(
        self,
        messages: list[dict],
        system: str | None = None,
        model_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Call converse and extract the text response."""
        result = self.converse(
            messages=messages,
            system=system,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result["output"]["message"]["content"][0]["text"]


_default_client: BedrockClient | None = None


def _get_client() -> BedrockClient:
    global _default_client
    if _default_client is None:
        _default_client = BedrockClient()
    return _default_client


def call_llm(
    messages: list[dict],
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Convenience function: call Bedrock and return text response."""
    client = _get_client()
    return client.converse_text(
        messages=messages,
        system=system,
        model_id=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def format_messages_for_bedrock(messages: list[dict]) -> list[dict]:
    """Convert simple {role, content} messages to Bedrock format."""
    bedrock_msgs = []
    for msg in messages:
        bedrock_msgs.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}],
        })
    return bedrock_msgs
