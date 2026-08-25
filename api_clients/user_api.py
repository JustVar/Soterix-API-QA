"""User-related API client."""
from __future__ import annotations

from typing import Any

from .base_api_client import BaseAPIClient


class UserAPI(BaseAPIClient):
    def get_user_session(self) -> dict[str, Any]:
        path = "/REST/central/user/session"
        r = self.get(path)
        r.raise_for_status()
        return r.json()

    def get_user_roles(self) -> list[dict[str, Any]]:
        path = "/REST/central/userprofile/roles"
        r = self.get(path)
        r.raise_for_status()
        return r.json()

    def validate_session_response(self, data: Any) -> bool:
        """Validate session response has expected structure

        Expected shape (example):
        {
          "status": 2000,
          "code": 200,
          "description": "OK",
          "message": "Successfully Retrieved!",
          "result": [{
            "streamer": "webrtc",
            "JSESSIONID": "cf6fe...",
            "userId": "user@example.com"
          }]
        }
        """
        if not data or not isinstance(data, dict):
            return False
        # Check for success code
        if data.get("code") != 200:
            return False
        # Check for result list with at least one entry
        result = data.get("result", [])
        if not result or len(result) == 0:
            return False
        # First result must contain userId
        first = result[0]
        if not isinstance(first, dict):
            return False
        return "userId" in first
