"""Orchestration: bring the Notion tickets database in line with Movidesk."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from . import tickets as T
from .config import Settings
from .notion import NotionClient
from .state import NotifiedStore
from .telegram import Telegram

log = logging.getLogger(__name__)


@dataclass
class Result:
    created: int = 0
    updated: int = 0
    archived: int = 0
    alerts: int = 0


def run(
    raw_tickets: list[dict],
    notion: NotionClient,
    telegram: Telegram,
    state: NotifiedStore,
    settings: Settings,
) -> Result:
    index = notion.index_by_ticket(settings.notion_database_id)
    result = Result()
    seen: set[str] = set()

    for raw in raw_tickets:
        t = T.parse(raw)
        if not t.id:
            continue
        seen.add(t.id)

        # a ticket that left the open states → archive its Notion page
        if not t.is_open:
            if t.id in index:
                notion.archive(index[t.id], t.id)
                result.archived += 1
            continue

        # nobody assigned + keyword in the subject → alert once
        if t.unassigned and T.matches_keyword(t.subject, settings.keywords):
            tag = f"{t.id}_sem_responsavel"
            if not state.has(tag):
                telegram.send(T.alert_unassigned(t))
                state.add(tag)
                result.alerts += 1

        # assigned and has an asset → create / update the Notion page
        if t.fully_assigned:
            props = T.notion_properties(t)
            if t.id in index:
                notion.update(index[t.id], props, t.id)
                result.updated += 1
            else:
                notion.create(settings.notion_database_id, props, t.description)
                result.created += 1

            tag = f"{t.id}_atribuicao_completa"
            if not state.has(tag):
                telegram.send(T.alert_assigned(t))
                state.add(tag)
                result.alerts += 1

    # Notion pages whose ticket is gone from Movidesk → archive
    for ticket_id, page_id in index.items():
        if ticket_id not in seen:
            notion.archive(page_id, ticket_id)
            result.archived += 1

    log.info(
        "done: %d created, %d updated, %d archived, %d alerts",
        result.created, result.updated, result.archived, result.alerts,
    )
    return result
