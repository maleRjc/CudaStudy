"""
Single, well-behaved DeepSeek chat client used by every generator.

Design goals:
- One place that knows about retries, timeouts, JSON-mode and fence stripping.
- Typed errors so callers can distinguish "no key" from "auth failed" from
  "network flaked" and make an informed fallback decision.
- Never log the API key, only a short SHA-256 fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional

import requests

import config


class DeepSeekError(RuntimeError):
    """Base error for all DeepSeek interactions."""

    def __init__(self, message: str, *, kind: str = "error", status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


class DeepSeekUnavailable(DeepSeekError):
    """No API key configured - callers should use the deterministic fallback."""


class DeepSeekAuthError(DeepSeekError):
    """Key rejected by the API."""


class DeepSeekTransientError(DeepSeekError):
    """Network/timeout/5xx - retryable in principle, already retried here."""


def key_fingerprint(key: str) -> str:
    if not key:
        return "none"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _complete_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort repair for a JSON object cut off by the token limit.

    Tries the last few ``}`` positions, closes any open arrays/objects and
    parses the result. Returns None when nothing usable can be recovered.
    """
    start = text.find("{")
    if start < 0:
        return None
    payload = text[start:]
    closing_positions = [index for index, char in enumerate(payload) if char == "}"][-60:]

    for end in reversed(closing_positions):
        prefix = payload[: end + 1]
        stack: list[str] = []
        in_string = False
        escaped = False
        valid = True
        for char in prefix:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char in "{[":
                stack.append(char)
            elif char in "}]":
                if not stack:
                    valid = False
                    break
                opening = stack.pop()
                if (opening, char) not in (("{", "}"), ("[", "]")):
                    valid = False
                    break
        if not valid or in_string:
            continue
        candidate = prefix + "".join("]" if item == "[" else "}" for item in reversed(stack))
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_json_payload(text: str) -> Dict[str, Any]:
    """Parse a model response that should contain a JSON object."""
    if not text or not text.strip():
        raise DeepSeekError("empty model response", kind="empty")

    cleaned = _strip_code_fence(text)
    for candidate in (cleaned, cleaned[cleaned.find("{"): cleaned.rfind("}") + 1] if "{" in cleaned else ""):
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
            if isinstance(value, list):
                return {"items": value}
        except json.JSONDecodeError:
            continue

    repaired = _complete_truncated_json(cleaned)
    if repaired:
        repaired["__salvaged__"] = True
        return repaired

    raise DeepSeekError(f"invalid JSON from model: {text[:200]!r}", kind="invalid_json")


class DeepSeekClient:
    """Thin wrapper around the OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.api_key = (api_key or config.api_key()).strip()
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.model = model or config.DEEPSEEK_MODEL
        self.timeout = int(timeout or config.DEEPSEEK_TIMEOUT)
        self._session = requests.Session()

    # -- capability ------------------------------------------------------
    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def describe(self) -> str:
        return f"model={self.model} endpoint={self.base_url} key=sha256:{key_fingerprint(self.api_key)}"

    # -- transport -------------------------------------------------------
    def _post(self, payload: Dict[str, Any], *, retries: int = 3) -> Dict[str, Any]:
        if not self.api_key:
            raise DeepSeekUnavailable("DEEPSEEK_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CudaStudyStudio/2.0",
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                response = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise DeepSeekTransientError(f"request failed after {retries} attempts: {exc}", kind="network") from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise DeepSeekError("malformed HTTP body", kind="bad_body", status=200) from exc

            if response.status_code in (401, 403):
                raise DeepSeekAuthError(
                    "DeepSeek rejected the API key (HTTP %s). Check DEEPSEEK_API_KEY." % response.status_code,
                    kind="auth",
                    status=response.status_code,
                )

            if response.status_code == 429 or response.status_code >= 500:
                last_error = DeepSeekTransientError(
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    kind="server",
                    status=response.status_code,
                )
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise last_error

            # 400/404/422 etc: not retryable, surface the reason.
            raise DeepSeekError(
                f"HTTP {response.status_code}: {response.text[:300]}",
                kind="client",
                status=response.status_code,
            )

        raise DeepSeekTransientError(f"request failed: {last_error}", kind="network")

    # -- chat ------------------------------------------------------------
    def chat_text(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": int(max_tokens or config.DEEPSEEK_MAX_TOKENS),
        }
        data = self._post(payload)
        choices = data.get("choices") or []
        if not choices:
            raise DeepSeekError("response contained no choices", kind="bad_body")
        choice = choices[0]
        content = (choice.get("message") or {}).get("content") or ""
        if choice.get("finish_reason") == "length":
            raise DeepSeekError("model output truncated (finish_reason=length)", kind="truncated")
        return content

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": int(max_tokens or config.DEEPSEEK_MAX_TOKENS),
            "response_format": {"type": "json_object"},
        }
        data = self._post(payload)
        choices = data.get("choices") or []
        if not choices:
            raise DeepSeekError("response contained no choices", kind="bad_body")
        choice = choices[0]
        content = (choice.get("message") or {}).get("content") or ""
        if choice.get("finish_reason") == "length":
            raise DeepSeekError("model output truncated (finish_reason=length)", kind="truncated")
        return parse_json_payload(content)


_default_client: Optional[DeepSeekClient] = None
_default_signature = None


def default_client() -> DeepSeekClient:
    """Cached client that follows runtime key changes made through config.set_api_key()."""
    global _default_client, _default_signature
    signature = (config.api_key(), config.DEEPSEEK_BASE_URL, config.DEEPSEEK_MODEL)
    if _default_client is None or signature != _default_signature:
        _default_client = DeepSeekClient()
        _default_signature = signature
    return _default_client


def diagnose(client: Optional[DeepSeekClient] = None) -> Dict[str, Any]:
    """Cheap connectivity + auth probe used by check_env and the GUI."""
    client = client or default_client()
    if not client.available:
        return {
            "status": "FAIL",
            "detail": "未配置 DEEPSEEK_API_KEY —— 本版本已移除无 Key 兜底模式，无法生成讲稿",
            "advice": "复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY；或在 GUI 输入框中填写后重试。",
        }
    try:
        reply = client.chat_text(
            "You are a connectivity probe. Reply with exactly: OK",
            "ping",
            temperature=0.0,
            max_tokens=8,
        )
        return {
            "status": "PASS",
            "detail": f"连接成功 · {client.describe()} · reply={reply.strip()[:20]}",
            "advice": "",
        }
    except DeepSeekAuthError as exc:
        return {"status": "FAIL", "detail": str(exc), "advice": "请检查 API Key 是否正确、是否过期。"}
    except DeepSeekError as exc:
        return {
            "status": "WARN",
            "detail": f"端点不可用（{exc.kind}）: {str(exc)[:120]}",
            "advice": "检查网络/代理或 DEEPSEEK_BASE_URL；离线时系统会自动使用确定性引擎。",
        }
