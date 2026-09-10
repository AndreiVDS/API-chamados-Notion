"""Write side: a thin Notion client for the tickets database."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


class NotionClient:
    def __init__(self, session: requests.Session, token: str, dry_run: bool = False):
        self._session = session
        self._dry_run = dry_run
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": VERSION,
        }

    def index_by_ticket(self, database_id: str) -> dict[str, str]:
        """Map of {ticket number -> Notion page id} already in the database."""
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
                rich = page["properties"].get("Chamado", {}).get("rich_text", [])
                ticket_id = rich[0]["text"]["content"] if rich else ""
                if ticket_id:
                    index[ticket_id] = page["id"]
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        log.info("Notion: %d pages indexed", len(index))
        return index

    def create(self, database_id: str, properties: dict, description: str) -> None:
        if self._dry_run:
            log.info("[dry-run] would create page for %s", _ticket_no(properties))
            return
        body = {
            "parent": {"database_id": database_id},
            "properties": properties,
            "children": [_paragraph(description)],
        }
        resp = self._session.post(f"{API}/pages", headers=self._headers, json=body)
        _log_result(resp, "create", _ticket_no(properties))

    def update(self, page_id: str, properties: dict, ticket_id: str) -> None:
        if self._dry_run:
            log.info("[dry-run] would update %s", ticket_id)
            return
        resp = self._session.patch(
            f"{API}/pages/{page_id}", headers=self._headers, json={"properties": properties}
        )
        _log_result(resp, "update", ticket_id)

    def archive(self, page_id: str, ticket_id: str) -> None:
        if self._dry_run:
            log.info("[dry-run] would archive %s", ticket_id)
            return
        resp = self._session.patch(
            f"{API}/pages/{page_id}", headers=self._headers, json={"archived": True}
        )
        _log_result(resp, "archive", ticket_id)


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _ticket_no(properties: dict) -> str:
    try:
        return properties["Chamado"]["rich_text"][0]["text"]["content"]
    except (KeyError, IndexError):
        return "?"


def _log_result(resp: requests.Response, action: str, ticket_id: str) -> None:
    if resp.status_code == 200:
        log.info("Notion %s ok: %s", action, ticket_id)
    else:
        log.error("Notion %s %s (%s): %s", action, ticket_id, resp.status_code, resp.text[:300])
