"""Telegram alerts."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


class Telegram:
    def __init__(self, session: requests.Session, bot_token: str, chat_id: str, dry_run: bool = False):
        self._session = session
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._dry_run = dry_run
        self.enabled = bool(bot_token and chat_id)

    def send(self, text: str) -> None:
        if not self.enabled:
            return
        if self._dry_run:
            log.info("[dry-run] telegram: %s", text.splitlines()[0])
            return
        resp = self._session.post(
            f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            data={"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"},
        )
        if resp.status_code != 200:
            log.error("Telegram %s: %s", resp.status_code, resp.text[:300])
