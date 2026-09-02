"""Dashboard API client."""
from __future__ import annotations

from typing import Any

from .base_api_client import BaseAPIClient


class DashboardAPI(BaseAPIClient):
    def get_site_status(self, site_id: int) -> dict[str, Any]:
        path = f"/REST/dashboard/site/{site_id}/status"
        r = self.get(path)
        r.raise_for_status()
        data = r.json()
        return data

    def get_shared_widgets(self, customer_id: int) -> dict[str, Any]:
        path = f"/REST/dashboard/sharedwidgets/{customer_id}/data"
        r = self.get(path)
        r.raise_for_status()
        return r.json()

    def validate_status_response(self, data: dict[str, Any]) -> bool:
        # Minimal validation: must include camera counts or system status
        if not isinstance(data, dict):
            return False
        # presence of some known keys
        return any(k in data for k in ("status", "cameras", "getofflinecameras", "widget"))
