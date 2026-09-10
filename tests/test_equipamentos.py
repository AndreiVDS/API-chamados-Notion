from movidesk_notion.config import Settings
from movidesk_notion.equipamentos import occupied_by, run


def ticket(assets, status="Novo", client="Fiscal"):
    return {
        "id": 1,
        "subject": "x",
        "status": status,
        "clients": [{"businessName": client}] if client else [],
        "assets": [{"name": a} for a in assets],
    }


def test_occupied_by_only_counts_open_tickets_with_client_and_assets():
    raw = [
        ticket(["NB-1", "NB-2"]),
        ticket(["NB-3"], status="Fechado"),
        ticket([], client="X"),
    ]
    assert occupied_by(raw) == {"NB-1": "Fiscal", "NB-2": "Fiscal"}


class FakeEquip:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def index_by_name(self, _db):
        return dict(self.rows)

    def set_status(self, _page_id, name, status, user):
        self.calls.append((name, status, user))


def test_run_marks_busy_and_free():
    s = Settings(movidesk_token="m", notion_token="n", notion_database_id="d",
                 notion_equipamentos_db="eq")
    fake = FakeEquip({"NB-1": "p1", "NB-2": "p2"})
    run([ticket(["NB-1"])], fake, s)
    assert ("NB-1", "Ocupado", "Fiscal") in fake.calls
    assert ("NB-2", "Disponível", "") in fake.calls


def test_run_noop_without_db():
    s = Settings(movidesk_token="m", notion_token="n", notion_database_id="d")
    assert run([], FakeEquip({}), s) == 0
