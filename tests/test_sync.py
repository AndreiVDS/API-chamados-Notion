from movidesk_notion.config import Settings
from movidesk_notion.state import NotifiedStore
from movidesk_notion.sync import run


class FakeNotion:
    def __init__(self, existing=None):
        self.existing = existing or {}
        self.created, self.updated, self.archived = [], [], []

    def index_by_ticket(self, _db):
        return dict(self.existing)

    def create(self, _db, properties, _description):
        self.created.append(properties["Chamado"]["rich_text"][0]["text"]["content"])

    def update(self, _page_id, properties, ticket_id):
        self.updated.append(ticket_id)

    def archive(self, _page_id, ticket_id):
        self.archived.append(ticket_id)


class FakeTelegram:
    enabled = True

    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)


def settings(tmp_path):
    return Settings(
        movidesk_token="m",
        notion_token="n",
        notion_database_id="db",
        telegram_bot_token="b",
        telegram_chat_id="c",
        state_file=str(tmp_path / "s.json"),
        keywords=["notebook"],
    )


def ticket(tid, status="Novo", owner=True, assets=("NB-1",), subject="pedido de notebook"):
    return {
        "id": tid,
        "subject": subject,
        "status": status,
        "owner": {"businessName": "Andrei"} if owner else None,
        "clients": [{"businessName": "Fiscal"}],
        "assets": [{"name": a} for a in assets],
        "createdDate": "2026-01-01",
        "actions": [{"description": "abertura"}],
    }


def test_creates_new_assigned_ticket_and_alerts(tmp_path):
    notion, tg = FakeNotion(), FakeTelegram()
    run([ticket("1")], notion, tg, NotifiedStore(str(tmp_path / "s.json")), settings(tmp_path))
    assert notion.created == ["1"]
    assert notion.updated == []
    assert any("registrado no Notion" in m for m in tg.sent)


def test_updates_when_already_indexed(tmp_path):
    notion = FakeNotion(existing={"1": "page-1"})
    run([ticket("1")], notion, FakeTelegram(), NotifiedStore(str(tmp_path / "s.json")), settings(tmp_path))
    assert notion.updated == ["1"]
    assert notion.created == []


def test_archives_ticket_that_left_movidesk(tmp_path):
    notion = FakeNotion(existing={"9": "page-9"})
    run([], notion, FakeTelegram(), NotifiedStore(str(tmp_path / "s.json")), settings(tmp_path))
    assert notion.archived == ["9"]


def test_archives_closed_ticket(tmp_path):
    notion = FakeNotion(existing={"1": "page-1"})
    run([ticket("1", status="Fechado")], notion, FakeTelegram(),
        NotifiedStore(str(tmp_path / "s.json")), settings(tmp_path))
    assert notion.archived == ["1"]


def test_alerts_unassigned_keyword_ticket_once(tmp_path):
    tg = FakeTelegram()
    state = NotifiedStore(str(tmp_path / "s.json"))
    raw = [ticket("5", owner=False, assets=())]
    run(raw, FakeNotion(), tg, state, settings(tmp_path))
    run(raw, FakeNotion(), tg, state, settings(tmp_path))  # second run: no repeat
    assert sum("sem atribuição" in m for m in tg.sent) == 1


def test_non_keyword_unassigned_ticket_is_silent(tmp_path):
    tg = FakeTelegram()
    run([ticket("6", owner=False, assets=(), subject="impressora travou")],
        FakeNotion(), tg, NotifiedStore(str(tmp_path / "s.json")), settings(tmp_path))
    assert tg.sent == []
