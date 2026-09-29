"""Download the internal API's OpenAPI spec from the configured server.

The host comes from config/env/<ENV>.py (api_base_url), so a server change
is one edit. The spec lands in schemas/openapi_spec_<ENV>.json. When the
optional package openapi-spec-validator is installed, the file is validated
too. A summary (endpoint and schema counts, auth methods, tags) prints last.

Usage:
    python tools/download_openapi_spec.py            # ENV from .env, default qa
    ENV=other python tools/download_openapi_spec.py  # config/env/other.py

The vendor's spec lags the deployed API. docs/INTERNAL_API_INVENTORY.md
holds the shapes measured on the server and is the reference for tests.
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# schemas/ at the repo root is where the committed specs live
OUT_DIR = ROOT / "schemas"


def download(url: str, out_path: Path, verify: bool) -> bool:
    print(f"Downloading {url} -> {out_path}")
    try:
        r = requests.get(url, timeout=30, verify=verify)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Download failed: {e}")
        return False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True


def summarize(spec: dict) -> dict:
    paths = spec.get("paths", {})
    total_endpoints = sum(len(v.keys()) for v in paths.values())
    components = spec.get("components", {})
    schemas = components.get("schemas", {})
    security_schemes = components.get("securitySchemes", {})
    tags = spec.get("tags", [])
    tag_names = [t.get("name") for t in tags]
    return {
        "total_endpoints": total_endpoints,
        "total_schemas": len(schemas),
        "auth_methods": list(security_schemes.keys()),
        "tags": tag_names,
    }


def validate_spec_file(path: Path) -> bool | None:
    """True or False from the validator, None when it is not installed."""
    try:
        from openapi_spec_validator import validate_spec
    except ImportError:
        print("openapi-spec-validator is not installed, so the spec is not validated. "
              "Install it to validate: pip install openapi-spec-validator")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
        validate_spec(spec)
        return True
    except Exception as e:
        print(f"Spec validation failed for {path}: {e}")
        return False


def main():
    from api_clients.tls import ssl_verify
    from config.base_config import config

    env = (os.environ.get("ENV") or "qa").strip().lower()
    api_base_url = config.get("api_base_url", config["base_url"]).rstrip("/")
    url = f"{api_base_url}/v3/api-docs"
    out_path = OUT_DIR / f"openapi_spec_{env}.json"

    # The TLS rule of the clients (api_clients/tls.py): verify only when
    # SSL_VERIFY is true.
    if not download(url, out_path, ssl_verify()):
        sys.exit(1)

    spec = json.loads(out_path.read_text(encoding="utf-8"))
    result = summarize(spec)
    result["valid"] = validate_spec_file(out_path)
    print(json.dumps({env: result}, indent=2))


if __name__ == '__main__':
    main()
