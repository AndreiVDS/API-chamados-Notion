"""Pure helpers — no I/O. Turn a raw Movidesk ticket into what Notion / Telegram need."""

from __future__ import annotations

from dataclasses import dataclass

from .config import OPEN_STATUSES


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    status: str  # lowercased
    has_owner: bool
    owner_name: str
    client: str
    assets: list[str]
    created_date: str
    description: str

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def notion_status(self) -> str:
        return OPEN_STATUSES.get(self.status, "")

    @property
    def unassigned(self) -> bool:
        return not self.has_owner and not self.assets

    @property
    def fully_assigned(self) -> bool:
        return self.has_owner and bool(self.assets)


def parse(raw: dict) -> Ticket:
    owner = raw.get("owner") or {}
    clients = raw.get("clients") or []
    actions = raw.get("actions") or [{}]
    return Ticket(
        id=str(raw.get("id", "")),
        subject=raw.get("subject", "") or "",
        status=(raw.get("status", "") or "").lower(),
        has_owner=bool(raw.get("owner")),
        owner_name=owner.get("businessName", "") if owner else "",
        client=clients[0]["businessName"] if clients else "Sem cliente",
        assets=[a["name"] for a in (raw.get("assets") or [])],
        created_date=raw.get("createdDate", "") or "Sem data",
        description=(actions[0].get("description") or raw.get("justification") or "Sem descrição"),
    )


def matches_keyword(subject: str, keywords: list[str]) -> bool:
    low = subject.lower()
    return any(k in low for k in keywords)


def notion_properties(t: Ticket) -> dict:
    def rt(text: str) -> dict:
        return {"rich_text": [{"text": {"content": text}}]}

    return {
        "Titulo": {"title": [{"text": {"content": t.subject or "Sem título"}}]},
        "Chamado": rt(t.id),
        "Solicitante": rt(t.client),
        "Responsavel": rt(t.owner_name),
        "Ativo": rt(", ".join(t.assets)),
        "Status": {"status": {"name": t.notion_status}},
    }


def alert_unassigned(t: Ticket) -> str:
    return (
        "🚨 Chamado sem atribuição com palavra-chave!\n\n"
        f"🔖 Título: {t.subject or 'Sem título'}\n"
        f"🆔 Número: `{t.id}`\n"
        f"👤 Solicitante: {t.client}\n"
        f"🗓️ Data: `{t.created_date}`\n"
    )


def alert_assigned(t: Ticket) -> str:
    return (
        "📢 Chamado atribuído e registrado no Notion!\n\n"
        f"🔖 Título: {t.subject or 'Sem título'}\n"
        f"🆔 Número: `{t.id}`\n"
        f"👤 Solicitante: {t.client}\n"
        f"👨‍💻 Responsável: {t.owner_name}\n"
        f"💻 Equipamento: {', '.join(t.assets)}\n"
        f"🗓️ Data: `{t.created_date}`\n"
    )
