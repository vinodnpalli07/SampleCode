"""Client wrapper for Bamboo REST API interactions."""

from __future__ import annotations

from typing import Any

import httpx

from .config import get_settings


class BambooClient:
    def __init__(self) -> None:
        cfg = get_settings().bamboo
        self._base_url = cfg.base_url.rstrip("/")
        self._auth = None
        headers: dict[str, str] = {"Accept": "application/json"}
        if cfg.personal_access_token:
            headers["Authorization"] = f"Bearer {cfg.personal_access_token}"
        elif cfg.username and cfg.password:
            self._auth = (cfg.username, cfg.password)

        self._client = httpx.AsyncClient(base_url=self._base_url, headers=headers, auth=self._auth)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_build_result(self, result_key: str) -> dict[str, Any]:
        """Fetch a Bamboo build result and associated metadata."""

        endpoint = (
            f"/rest/api/latest/result/{result_key}?"
            "expand=testResults.failedTests,testResults.passedTests"
        )
        response = await self._client.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data

    async def get_build_log(self, result_key: str) -> str:
        """Retrieve the raw log for a Bamboo build."""

        endpoint = f"/download/result/{result_key}/log"
        response = await self._client.get(endpoint)
        response.raise_for_status()
        return response.text

    async def list_recent_results(self, plan_key: str, max_results: int = 25) -> list[dict[str, Any]]:
        """Return a lightweight listing of recent results for a plan."""

        endpoint = f"/rest/api/latest/result/{plan_key}.json?max-results={max_results}"
        response = await self._client.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("results", {}).get("result", [])


async def fetch_bamboo_run(result_key: str) -> tuple[dict[str, Any], str]:
    """Convenience helper to download both result metadata and logs."""

    client = BambooClient()
    try:
        metadata = await client.get_build_result(result_key)
        log_text = await client.get_build_log(result_key)
    finally:
        await client.close()
    return metadata, log_text

