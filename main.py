"""CLI entrypoint.

    python main.py                # one sync run
    python main.py --dry-run      # log what would change, touch nothing
    python main.py --state-file /tmp/notified.json
"""

from __future__ import annotations

import argparse
import logging
import sys

from movidesk_notion import equipamentos as equip
from movidesk_notion.config import Settings
from movidesk_notion.http_client import build_session
from movidesk_notion.movidesk import fetch_open_tickets
from movidesk_notion.notion import NotionClient
from movidesk_notion.state import NotifiedStore
from movidesk_notion.sync import run
from movidesk_notion.telegram import Telegram


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Movidesk with Notion.")
    parser.add_argument(
        "--mode",
        choices=("chamados", "equipamentos"),
        default="chamados",
        help="chamados: tickets -> Notion + Telegram (default). equipamentos: mark assets Ocupado/Disponível.",
    )
    parser.add_argument("--dry-run", action="store_true", help="log changes without writing")
    parser.add_argument("--state-file", help="override the notified-alerts file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    try:
        settings = Settings.from_env()
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 2

    if args.state_file:
        settings = Settings(**{**settings.__dict__, "state_file": args.state_file})

    session = build_session()
    raw = fetch_open_tickets(session, settings.movidesk_token)

    if args.mode == "equipamentos":
        equip.run(raw, equip.EquipamentosNotion(session, settings.notion_token, args.dry_run), settings)
        return 0

    notion = NotionClient(session, settings.notion_token, dry_run=args.dry_run)
    telegram = Telegram(
        session, settings.telegram_bot_token, settings.telegram_chat_id, dry_run=args.dry_run
    )
    state = NotifiedStore(settings.state_file)
    run(raw, notion, telegram, state, settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
