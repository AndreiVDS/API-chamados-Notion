"""Remembers which alerts were already sent, so we don't ping twice."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class NotifiedStore:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._tags: set[str] = self._load()

    def _load(self) -> set[str]:
        if not self._path.exists():
            return set()
        try:
            return set(json.loads(self._path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("state file unreadable (%s), starting fresh", exc)
            return set()

    def has(self, tag: str) -> bool:
        return tag in self._tags

    def add(self, tag: str) -> None:
        self._tags.add(tag)
        try:
            self._path.write_text(json.dumps(sorted(self._tags)), encoding="utf-8")
        except OSError as exc:
            log.error("could not persist state: %s", exc)
