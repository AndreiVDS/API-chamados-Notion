"""Read side: the Movidesk help-desk API."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.movidesk.com/public/v1/tickets"
PAGE_SIZE = 85


def fetch_open_tickets(session: requests.Session, token: str) -> list[dict]:
    """All tickets currently 'Novo' or 'Em atendimento', newest first, paged."""
    tickets: list[dict] = []
    skip = 0
    while True:
        params = {
            "token": token,
            "$orderby": "createdDate desc",
            "$skip": skip,
            "$top": PAGE_SIZE,
            "$select": "id,subject,status,owner,createdDate,clients,assets",
            "$expand": "owner,clients,assets,actions",
            "$filter": "(status eq 'Novo' or status eq 'Em atendimento')",
        }
        resp = session.get(BASE_URL, params=params)
        if resp.status_code != 200:
            log.error("Movidesk %s: %s", resp.status_code, resp.text[:300])
            break

        page = resp.json()
        if not page:
            break

        tickets.extend(page)
        skip += PAGE_SIZE

    log.info("Movidesk: %d open tickets", len(tickets))
    return tickets
