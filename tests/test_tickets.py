from movidesk_notion import tickets as T


def raw(**over):
    base = {
        "id": 123,
        "subject": "Preciso de um notebook novo",
        "status": "Novo",
        "owner": {"businessName": "Andrei"},
        "clients": [{"businessName": "Setor Fiscal"}],
        "assets": [{"name": "NB-014"}],
        "createdDate": "2026-01-02T10:00:00",
        "actions": [{"description": "chamado aberto pelo portal"}],
    }
    base.update(over)
    return base


def test_parse_extracts_fields():
    t = T.parse(raw())
    assert t.id == "123"
    assert t.status == "novo"
    assert t.client == "Setor Fiscal"
    assert t.owner_name == "Andrei"
    assert t.assets == ["NB-014"]
    assert t.description == "chamado aberto pelo portal"


def test_parse_tolerates_missing_pieces():
    t = T.parse({"id": 9, "status": "Fechado"})
    assert t.client == "Sem cliente"
    assert t.assets == []
    assert t.description == "Sem descrição"
    assert not t.is_open


def test_open_and_assignment_flags():
    assert T.parse(raw()).fully_assigned
    assert T.parse(raw()).is_open
    unassigned = T.parse(raw(owner=None, assets=[]))
    assert unassigned.unassigned
    assert not unassigned.fully_assigned


def test_keyword_match_is_case_insensitive():
    assert T.matches_keyword("Comprar NOTEBOOK", ["notebook"])
    assert not T.matches_keyword("Erro no sistema", ["notebook", "microfone"])


def test_notion_properties_shape():
    props = T.notion_properties(T.parse(raw()))
    assert props["Chamado"]["rich_text"][0]["text"]["content"] == "123"
    assert props["Status"]["status"]["name"] == "Novo"
    assert props["Ativo"]["rich_text"][0]["text"]["content"] == "NB-014"
