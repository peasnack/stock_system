import json
import logging
import os
from pathlib import Path
from typing import Any

from config import OPENAI_MODEL
from src.ai.prompt_builder import build_messages

logger = logging.getLogger(__name__)


def _load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_json_response(content: str) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("AI_ERROR: response is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("AI_ERROR: response JSON must be an object")
    return data


def call_openai_decision(market_context: dict[str, Any]) -> dict[str, Any]:
    _load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)

    if not api_key:
        logger.error("OpenAI API key is not configured")
        return {"status": "AI_ERROR", "error": "AI_ERROR: OPENAI_API_KEY is not configured"}

    try:
        from openai import OpenAI
    except ImportError:
        logger.exception("OpenAI Python SDK is not installed")
        return {"status": "AI_ERROR", "error": "AI_ERROR: openai Python SDK is not installed"}

    system_prompt, user_prompt = build_messages(market_context)
    try:
        client = OpenAI(api_key=api_key, timeout=60.0)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return {
            "status": "OK",
            "model": model,
            "decision": _parse_json_response(content),
        }
    except Exception as exc:
        logger.exception("OpenAI decision call failed")
        return {"status": "AI_ERROR", "model": model, "error": f"AI_ERROR: {exc}"}
