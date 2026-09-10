# Movidesk → Notion sync

A Python automation that keeps a **Notion database in sync with the Movidesk help-desk**
and raises **Telegram alerts** for tickets that need attention. Built to remove manual
copy-paste from a real IT support workflow.

## What it does

- Polls the **Movidesk** API for open tickets (`Novo`, `Em atendimento`), paging through all results.
- For each ticket with an assignee **and** a linked asset, **creates or updates** a page in a
  Notion database (title, ticket number, requester, assignee, equipment, status, description).
- **Archives** Notion pages whose ticket is no longer open in Movidesk, so the board stays clean.
- Sends a **Telegram message** when a ticket matching a keyword list (notebook, sound box,
  meeting room, microphone, …) has **no assignee and no asset** — i.e. it is falling through the cracks.
- Remembers what it already alerted about in `chamados_notificados.json` to avoid duplicate pings.

`equipamentos.py` is a companion script that syncs the equipment/asset list into its own Notion database.

## Stack

`Python` · `requests` · `python-dotenv` · Movidesk REST API · Notion API (`2022-06-28`) · Telegram Bot API

## Running

```bash
pip install requests python-dotenv
python MAIN_16_04_2025.py
```

Create a `.env` file (never commit it):

```env
MOVIDESK_API_TOKEN_TESTES=...
NOTION_API_TOKEN_TESTES=...
NOTION_DATABASE_ID_TESTES=...
NOTION_EQUIPAMENTOS_DB_TESTES=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Run it on a schedule (cron / Task Scheduler) to keep the board live.

## Notes

- The Notion database must have the properties the script writes to: `Titulo`, `Chamado`,
  `Solicitante`, `Responsavel`, `Ativo`, `Status`.
- All credentials are read from the environment — nothing sensitive is stored in the code.
