"""Authentication helper for API clients."""
from __future__ import annotations

import hashlib
import os
import time

import requests
import urllib3

from .tls import ssl_verify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# The web app authenticates against this endpoint. The other login endpoint
# on the server needs a token that only the browser can produce, so an API
# client cannot use it.
_LOGIN_PATH = "/REST/central/user/login"


def _login_username_label() -> str:
    """Return the fixed username label the login request carries.

    The web app sends one fixed label in the `username` field for every
    account; `accountid` carries the real email. The label is a server
    setting, so it lives in .env as LOGIN_USERNAME_LABEL, not in code. It is
    read at call time because .env is loaded after this module is imported.
    """
    return os.environ.get("LOGIN_USERNAME_LABEL", "")


class AuthHelper:
    def __init__(self, base_url: str):
        # Normalize base_url to include /v-apiserver if not present so
        # auth helper paths can use '/REST/...' directly.
        b = (base_url or "").rstrip("/")
        if not b.endswith("/v-apiserver"):
            b = b + "/v-apiserver"
        self.base_url = b
        self._token: str | None = None
        self._token_expiry: float = 0.0
        # Session cache settings. The cache is keyed on the server AND the
        # account (see _load_cached_token): keyed on the server alone, a
        # changed QA_USER would reuse the previous account's session for up
        # to CACHE_MAX_AGE_HOURS and the wrong account would run the suite.
        self.CACHE_FILE = ".session_cache"
        self.CACHE_MAX_AGE_HOURS = 8

    def _load_cached_token(self, email: str) -> str | None:
        """Load token from cache if valid for this server and this account."""
        import json as _json

        print("[AUTH CACHE] Checking for cached token...")
        print(f"[AUTH CACHE] Cache file exists: {os.path.exists(self.CACHE_FILE)}")
        if not os.path.exists(self.CACHE_FILE):
            return None

        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                cache = _json.load(f)

            print(f"[AUTH CACHE] Loaded: {dict(cache, token='***') if isinstance(cache, dict) else cache}")

            cached_time = cache.get("timestamp", 0)
            age_hours = (time.time() - cached_time) / 3600
            if age_hours > self.CACHE_MAX_AGE_HOURS:
                print(f"[AUTH] Cache expired ({age_hours:.1f} hours old)")
                try:
                    os.remove(self.CACHE_FILE)
                except OSError:
                    pass
                return None

            token = cache.get("token")
            base_url = cache.get("base_url")
            cached_email = cache.get("email")

            print(f"[AUTH CACHE] Base URL match: {base_url} == {self.base_url}")

            # Ensure cached token is for the same base_url
            if base_url and base_url != self.base_url:
                print(f"[AUTH] Cache entry base_url mismatch: {base_url} != {self.base_url}")
                return None

            # Ensure cached token is for the same account. A cache written
            # without an email (an older layout) is a miss, never a hit.
            if cached_email != email:
                print(f"[AUTH] Cache entry account mismatch: {cached_email} != {email}")
                return None

            # Quick validation
            if token and self._validate_token(token):
                print(f"[AUTH] Using cached token ({age_hours:.1f} hours old)")
                return token
            else:
                print("[AUTH] Cached token invalid, will re-login")
                try:
                    os.remove(self.CACHE_FILE)
                except OSError:
                    pass
                return None

        except Exception as e:  # noqa: BLE001 - a corrupt cache falls through to a fresh login
            print(f"[AUTH] Cache read error: {e}")
            return None

    def _save_token_to_cache(self, token: str, email: str) -> None:
        """Save token to cache"""
        import json as _json

        cache = {"token": token, "base_url": self.base_url, "email": email,
                 "timestamp": time.time()}
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                _json.dump(cache, f)
            print("[AUTH] Token saved to cache")
        except OSError as e:
            print(f"[AUTH] Failed to save token cache: {e}")

    def _validate_token(self, token: str) -> bool:
        """Quick check if token is still valid"""
        try:
            headers = {"Cookie": f"JSESSIONID={token}"}
            url = f"{self.base_url}/REST/central/user/session"
            r = requests.get(url, headers=headers, verify=ssl_verify(), timeout=10)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _api_login(self, email: str, password: str) -> str:
        """Authenticate over HTTP and return the JSESSIONID. No browser involved.

        Mirrors what the web app does: POST a SHA512 hex digest of the
        password, never the plaintext, to the login path.

        Raises RuntimeError with a message that says which of the three distinct
        failure modes occurred, because they need completely different fixes.
        """
        label = _login_username_label()
        if not label:
            raise RuntimeError(
                "LOGIN_USERNAME_LABEL is blank in .env. The login request carries "
                "the fixed username label the web app sends. Set it, then rerun."
            )
        url = f"{self.base_url}{_LOGIN_PATH}"
        payload = {
            "accountid": email,
            "username": label,
            "password": hashlib.sha512(password.encode("utf-8")).hexdigest(),
        }

        try:
            r = requests.post(url, json=payload, timeout=20, verify=ssl_verify())
        except requests.RequestException as e:
            raise RuntimeError(
                f"Could not reach the API at {url}. Check base_url in config/env/, "
                f"the network and the VPN. ({type(e).__name__}: {e})"
            ) from e

        # The server distinguishes 'no such user' from 'wrong password', and the
        # difference tells you whether the credential or the server is wrong.
        if r.status_code == 404:
            raise RuntimeError(
                f"No account '{email}' exists on {self.base_url}. Each server has "
                f"its own accounts. Check QA_USER in .env and base_url in "
                f"config/env/ (ENV selects the file)."
            )
        if r.status_code == 400:
            raise RuntimeError(
                f"Account '{email}' exists on {self.base_url} but the password was "
                f"rejected. The stored password is most likely stale -- refresh it in "
                f".env. (If it is definitely correct, check LOGIN_USERNAME_LABEL in "
                f".env: the login request carries that label.)"
            )
        if r.status_code != 200:
            raise RuntimeError(
                f"Unexpected {r.status_code} from {url}: {r.text[:300]}"
            )

        # Token arrives in the body; the Set-Cookie header is a fallback.
        token = None
        try:
            result = (r.json().get("result") or [{}])[0]
            token = result.get("JSESSIONID")
        except Exception:  # noqa: BLE001, S110 - any body shape falls back to the cookie
            pass
        token = token or r.cookies.get("JSESSIONID")

        if not token:
            raise RuntimeError(
                f"Login returned 200 but no JSESSIONID was found in the response "
                f"body or cookies: {r.text[:300]}"
            )
        return token

    def login(self, email: str, password: str) -> str:
        """Return a JSESSIONID for the given credentials.

        Order: cached token -> in-memory token -> HTTP login. There is no
        browser fallback in this repo: a login failure raises with a message
        that says whether the account, the password, or the host is wrong.
        """
        # 1) Try cached token first
        cached = self._load_cached_token(email)
        if cached:
            self._token = cached
            self._token_expiry = time.time() + 1800
            print("[AUTH] Returning cached token")
            return cached

        # 2) If in-memory token still fresh, use it
        if self._token and time.time() < self._token_expiry - 30:
            return self._token

        # 3) Browser-free HTTP login
        token = self._api_login(email, password)
        self._token = token
        self._token_expiry = time.time() + 1800
        try:
            self._save_token_to_cache(token, email)
        except Exception:  # noqa: BLE001, S110 - a cache write failure must not fail the login
            pass
        print("[AUTH] API login succeeded")
        return token
