"""Base API client with simple schema validation and logging.

Every request also lands in a bounded in-memory exchange log (the last
EXCHANGE_LIMIT calls per client). The internal-suite conftest attaches that
log to the HTML report when a test fails, so a failure shows the calls that
led to it, not only the assertion. Secrets are masked before they are stored.
"""
from __future__ import annotations

import itertools
import json
import logging
import os
import re
import time
import weakref
from collections import deque
from typing import Any, Dict, Optional

import requests
import urllib3
from jsonschema import validate as jsonschema_validate, ValidationError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_PATH = os.path.join(ROOT, "logs", "api_requests.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
# Named logger with its own handler: keeps the process root logger untouched
# so other suites in this repo can configure their own logging.
_logger = logging.getLogger("api_requests")
if not _logger.handlers:
    _handler = logging.FileHandler(LOG_PATH)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Exchange log. Each client keeps its last EXCHANGE_LIMIT exchanges. The
# module-level functions read and clear the logs of every live client, so a
# conftest hook can collect one test's calls no matter which client made them.
# ---------------------------------------------------------------------------
EXCHANGE_LIMIT = 20
BODY_LIMIT = 500
MASK = "***"

# Request keys whose value is a secret. Matched case-insensitively as a
# substring, so "password", "newPassword" and "JSESSIONID" all match.
_SECRET_KEY = re.compile(
    r"password|passwd|pwd|token|secret|jsessionid|authorization|cookie|api[-_]?key|vsaas-key",
    re.IGNORECASE,
)
_TEXT_MASKS = (
    # JSON member with a secret key: "JSESSIONID": "abc" -> "JSESSIONID": "***"
    (re.compile(r'("[^"]*(?:password|passwd|token|secret|jsessionid|api[-_]?key)[^"]*"\s*:\s*")[^"]*(")',
                re.IGNORECASE), r"\1" + MASK + r"\2"),
    # Cookie or query form: JSESSIONID=abc -> JSESSIONID=***
    (re.compile(r"(JSESSIONID=)[^;,&\s\"']+", re.IGNORECASE), r"\1" + MASK),
    # A bare SHA512 hex digest, the form the login password travels in.
    (re.compile(r"\b[0-9a-fA-F]{128}\b"), MASK),
)

_clients: weakref.WeakSet[BaseAPIClient] = weakref.WeakSet()
_sequence = itertools.count(1)


def mask_text(text: str) -> str:
    """Return text with passwords, tokens and JSESSIONID values replaced by ***."""
    for pattern, replacement in _TEXT_MASKS:
        text = pattern.sub(replacement, text)
    return text


def _mask_structure(value: Any) -> Any:
    """Return a copy of a JSON-like value with secret-keyed members replaced by ***."""
    if isinstance(value, dict):
        return {
            k: MASK if isinstance(k, str) and _SECRET_KEY.search(k) else _mask_structure(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_mask_structure(v) for v in value]
    return value


def _truncate(text: str, limit: int = BODY_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text)} chars total]"


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)


def _describe_request(json_body: Any, data: Any, files: Any) -> str:
    """Masked, truncated text of what the request carried in its body."""
    parts = []
    if json_body is not None:
        parts.append(_as_text(_mask_structure(json_body)))
    if data is not None:
        parts.append("data=" + _as_text(_mask_structure(data) if isinstance(data, (dict, list)) else data))
    if files:
        names = list(files.keys()) if isinstance(files, dict) else [f[0] for f in files]
        parts.append(f"files={names}")
    return _truncate(mask_text(" ".join(parts)))


def _describe_response(response: requests.Response) -> str:
    """Masked, truncated first BODY_LIMIT chars of the response body."""
    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith(("image/", "video/", "application/octet-stream")):
        return f"<{content_type}, {len(response.content)} bytes>"
    return _truncate(mask_text(response.text or ""))


def recent_exchanges() -> list[dict]:
    """The last EXCHANGE_LIMIT exchanges across every live client, oldest first."""
    exchanges = [e for client in list(_clients) for e in client.exchanges]
    exchanges.sort(key=lambda e: e["seq"])
    return exchanges[-EXCHANGE_LIMIT:]


def clear_exchanges() -> None:
    """Empty the exchange log of every live client."""
    for client in list(_clients):
        client.exchanges.clear()


def format_exchanges(exchanges: list[dict]) -> str:
    """Render exchanges as numbered plain-text lines for a report or the terminal."""
    lines = []
    for n, e in enumerate(exchanges, 1):
        if e["status"] is None:
            lines.append(f"{n}. {e['method']} {e['url']} -> no response ({e['error']})")
        else:
            lines.append(f"{n}. {e['method']} {e['url']} -> {e['status']} ({e['elapsed_ms']} ms)")
        if e["request_body"]:
            lines.append(f"   request: {e['request_body']}")
        if e["response_body"]:
            lines.append(f"   response: {e['response_body']}")
    return "\n".join(lines)


class BaseAPIClient:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout: int = 15, max_seconds: float = 2.0):
        # Normalize base_url and ensure API server prefix present.
        # Many deployments mount the API under `/v-apiserver`; if the
        # provided `base_url` does not already include that segment,
        # append it so client code can use paths like `/REST/...`.
        b = (base_url or "").rstrip("/")
        if not b.endswith("/v-apiserver"):
            b = b + "/v-apiserver"
        self.base_url = b
        self.token = token
        self.timeout = timeout
        self.max_seconds = max_seconds
        # Last EXCHANGE_LIMIT exchanges this client made. See recent_exchanges().
        self.exchanges: deque = deque(maxlen=EXCHANGE_LIMIT)
        _clients.add(self)
        # SSL verification: Check SSL_VERIFY env var first, then fall back to ENV-based logic
        ssl_verify_env = os.getenv("SSL_VERIFY", "").lower()
        if ssl_verify_env in ("false", "0", "no"):
            self.verify = False
        elif ssl_verify_env in ("true", "1", "yes"):
            self.verify = True
        else:
            # Default: disable SSL verification for non-production environments
            # This matches auth_helper.py logic and avoids SSL errors with self-signed certs
            env = os.getenv("ENV", "").lower()
            self.verify = False if env not in ("prod", "production") else True

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            # If token looks like a JSESSIONID (hex-like session id), send it as a Cookie
            import re
            t = str(self.token)
            if re.fullmatch(r"[0-9a-fA-F]{16,128}", t) or "=" in t:
                # If token includes '=', assume it's raw cookie string like 'JSESSIONID=...'
                if "=" in t:
                    # token may be e.g. 'JSESSIONID=abc; Path=/'
                    h["Cookie"] = t
                else:
                    h["Cookie"] = f"JSESSIONID={t}"
            else:
                h["Authorization"] = f"Bearer {self.token}"
        return h

    def _log(self, method: str, path: str, status: int, elapsed: float):
        _logger.info(f"{method} {path} -> {status} ({elapsed:.3f}s)")

    def _record(self, method: str, url: str, kwargs: dict, elapsed: float,
                response: requests.Response | None, error: BaseException | None) -> None:
        """Append one exchange to this client's log. Never raises."""
        try:
            self.exchanges.append({
                "seq": next(_sequence),
                "method": method,
                "url": mask_text(response.url if response is not None and response.url else url),
                "status": response.status_code if response is not None else None,
                "elapsed_ms": int(elapsed * 1000),
                "request_body": _describe_request(kwargs.get("json"), kwargs.get("data"), kwargs.get("files")),
                "response_body": _describe_response(response) if response is not None else "",
                "error": f"{type(error).__name__}: {error}" if error is not None else None,
            })
        except Exception as exc:  # noqa: BLE001 - a diagnostic aid must never fail a test
            _logger.warning(f"exchange log skipped {method} {url}: {exc}")

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        start = time.time()
        try:
            r = requests.request(method, url, headers=self._headers(), timeout=self.timeout, verify=self.verify, **kwargs)
        except Exception as exc:
            self._record(method, url, kwargs, time.time() - start, None, exc)
            raise
        elapsed = time.time() - start
        self._log(method, url, r.status_code, elapsed)
        self._record(method, url, kwargs, elapsed, r, None)
        return r

    def get(self, path: str, params: Dict[str, Any] | None = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: Any | None = None, data: Any | None = None,
             params: dict[str, Any] | None = None, files: Any | None = None) -> requests.Response:
        # `params` and `files` serve the few endpoints that take query
        # parameters plus a multipart part (POST /REST/clipbookmark).
        return self._request("POST", path, json=json, data=data, params=params, files=files)

    def put(self, path: str, json: Any | None = None) -> requests.Response:
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> requests.Response:
        return self._request("DELETE", path)

    def load_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        if not schema_name:
            return None
        # NOTE: in the old monorepo this path resolved to a directory that did
        # not exist, so schema validation silently never ran. It is live now.
        path = os.path.join(ROOT, "schemas", "responses", f"{schema_name}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_schema(self, response_json: Any, schema: Optional[Dict[str, Any]]):
        if not schema:
            return True
        try:
            jsonschema_validate(instance=response_json, schema=schema)
            return True
        except ValidationError as e:
            raise AssertionError(f"Schema validation failed: {e.message}")

    def assert_response_time(self, response: requests.Response, max_seconds: Optional[float] = None):
        ms = max_seconds or self.max_seconds
        elapsed = response.elapsed.total_seconds()
        if elapsed > ms:
            raise AssertionError(f"Response time {elapsed:.3f}s exceeded max {ms}s")
        return True
