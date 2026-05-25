#!/usr/bin/env python3
"""Cliente mínimo para a API do Notion usado pelos scripts de migração."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


NOTION_API_BASE = "https://api.notion.com/v1"
# Use the current Notion API version and the data_sources API shape introduced
# after 2025-09-03, instead of deprecated database-row endpoints.
NOTION_VERSION = "2026-03-11"


class NotionError(RuntimeError):
    """Erro retornado pela API do Notion."""


@dataclass
class NotionClient:
    token: str
    rate_limit_seconds: float = 0.35
    max_retries: int = 5

    @classmethod
    def from_env(cls) -> "NotionClient":
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise NotionError("Defina NOTION_TOKEN no ambiente.")
        return cls(token=token)

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    time.sleep(self.rate_limit_seconds)
                    data = response.read().decode("utf-8")
                    return json.loads(data) if data else {}
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                retry_after = exc.headers.get("Retry-After")
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_retries - 1:
                    delay = float(retry_after) if retry_after else min(2**attempt, 10)
                    time.sleep(delay)
                    continue
                raise NotionError(f"{method} {path} falhou ({exc.code}): {error_body}") from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries - 1:
                    time.sleep(min(2**attempt, 10))
                    continue
                raise NotionError(f"{method} {path} falhou: {exc}") from exc

        raise NotionError(f"{method} {path} falhou após {self.max_retries} tentativas.")

    def paginate(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        list_key: str = "results",
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page_payload = dict(payload or {})
            if cursor:
                page_payload["start_cursor"] = cursor
            response = self.request(method, path, page_payload if method != "GET" else None)
            results.extend(response.get(list_key, []))
            if not response.get("has_more"):
                return results
            cursor = response.get("next_cursor")


def rich_text(content: object | None) -> dict[str, Any]:
    if content is None:
        return {"rich_text": []}
    return {"rich_text": [{"text": {"content": str(content)[:2000]}}]}


def title(content: object) -> dict[str, Any]:
    return {"title": [{"text": {"content": str(content)[:2000]}}]}


def select(name: object | None) -> dict[str, Any]:
    if name in (None, ""):
        return {"select": None}
    return {"select": {"name": str(name)}}


def multi_select(values: list[object] | None) -> dict[str, Any]:
    if not values:
        return {"multi_select": []}
    return {"multi_select": [{"name": str(value)} for value in values if value not in (None, "")]}


def url(value: object | None) -> dict[str, Any]:
    return {"url": str(value) if value else None}


def number(value: object | None) -> dict[str, Any]:
    return {"number": value if isinstance(value, (int, float)) and not isinstance(value, bool) else None}


def date(value: object | None) -> dict[str, Any]:
    return {"date": {"start": str(value)} if value else None}


def checkbox(value: bool) -> dict[str, Any]:
    return {"checkbox": bool(value)}


def relation(page_ids: list[str] | None) -> dict[str, Any]:
    return {"relation": [{"id": page_id} for page_id in (page_ids or [])]}
