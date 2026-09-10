"""Second sync mode: mark equipment Ocupado / Disponível from the open tickets."""

from __future__ import annotations

import logging

import requests

from . import tickets as T
from .config import Settings

log = logging.getLogger(__name__)

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


class EquipamentosNotion:
    def __init__(self, session: requests.Session, token: str, dry_run: bool = False):
        self._session = session
        self._dry_run = dry_run
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": VERSION,
        }

    def index_by_name(self, database_id: str) -> dict[str, str]:
        index: dict[str, str] = {}
        cursor: str | None = None
        while True:
            payload: dict = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            resp = self._session.post(
                f"{API}/databases/{database_id}/query", headers=self._headers, json=payload
            )
            if resp.status_code != 200:
                log.error("Notion query %s: %s", resp.status_code, resp.text[:300])
                break
            data = resp.json()
            for page in data.get("results", []):
                title = page["properties"].get("Nome", {}).get("title", [])
                name = title[0]["text"]["content"] if title else ""
                if name:
                    index[name] = page["id"]
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        log.info("Notion: %d equipment rows", len(index))
        return index

    def set_status(self, page_id: str, name: str, status: str, user: str) -> None:
        if self._dry_run:
            log.info("[dry-run] %s -> %s (%s)", name, status, user or "---")
            return
        used_by = {"rich_text": [{"text": {"content": user}}]} if user else {"rich_text": []}
        resp = self._session.patch(
            f"{API}/pages/{page_id}",
            headers=self._headers,
            json={"properties": {"Status": {"status": {"name": status}}, "Utilizado por": used_by}},
        )
        if resp.status_code == 200:
            log.info("%s -> %s (%s)", name, status, user or "---")
        else:
            log.error("update %s %s: %s", name, resp.status_code, resp.text[:300])


def occupied_by(raw_tickets: list[dict]) -> dict[str, str]:
    """{asset name -> requesting client} across open tickets that have both."""
    out: dict[str, str] = {}
    for raw in raw_tickets:
        t = T.parse(raw)
        if t.is_open and t.assets and t.client:
            for asset in t.assets:
                out[asset] = t.client
    return out


def run(raw_tickets: list[dict], notion: EquipamentosNotion, settings: Settings) -> int:
    if not settings.notion_equipamentos_db:
        log.error("NOTION_EQUIPAMENTOS_DB_TESTES not set")
        return 0
    busy = occupied_by(raw_tickets)
    changed = 0
    for name, page_id in notion.index_by_name(settings.notion_equipamentos_db).items():
        if name in busy:
            notion.set_status(page_id, name, "Ocupado", busy[name])
        else:
            notion.set_status(page_id, name, "Disponível", "")
        changed += 1
    return changed
