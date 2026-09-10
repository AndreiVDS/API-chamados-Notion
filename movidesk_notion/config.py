"""Configuration, loaded from the environment. Nothing secret lives in the code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# Default keyword list. Override with KEYWORDS in the .env (comma-separated).
DEFAULT_KEYWORDS = [
    "notebook", "notebooks", "caixa de som", "som", "caixinha de som",
    "régua", "régua de energia", "filtro de luz", "extensão", "caixa",
    "reunião", "zoom", "meet", "microfone", "treinamento", "reserva",
    "reservas", "representante", "representantes", "home office", "home", "office",
]

OPEN_STATUSES = {"novo": "Novo", "em atendimento": "Em atendimento"}


def _keywords() -> list[str]:
    raw = os.getenv("KEYWORDS", "")
    if raw.strip():
        return [k.strip().lower() for k in raw.split(",") if k.strip()]
    return list(DEFAULT_KEYWORDS)


@dataclass(frozen=True)
class Settings:
    movidesk_token: str
    notion_token: str
    notion_database_id: str
    notion_equipamentos_db: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    state_file: str = "chamados_notificados.json"
    keywords: list[str] = field(default_factory=_keywords)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "MOVIDESK_API_TOKEN_TESTES": os.getenv("MOVIDESK_API_TOKEN_TESTES"),
            "NOTION_API_TOKEN_TESTES": os.getenv("NOTION_API_TOKEN_TESTES"),
            "NOTION_DATABASE_ID_TESTES": os.getenv("NOTION_DATABASE_ID_TESTES"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return cls(
            movidesk_token=required["MOVIDESK_API_TOKEN_TESTES"],
            notion_token=required["NOTION_API_TOKEN_TESTES"],
            notion_database_id=required["NOTION_DATABASE_ID_TESTES"],
            notion_equipamentos_db=os.getenv("NOTION_EQUIPAMENTOS_DB_TESTES", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            state_file=os.getenv("STATE_FILE", "chamados_notificados.json"),
        )
