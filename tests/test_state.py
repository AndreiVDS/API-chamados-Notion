from movidesk_notion.state import NotifiedStore


def test_round_trip(tmp_path):
    path = tmp_path / "notified.json"
    store = NotifiedStore(path)
    assert not store.has("123_x")

    store.add("123_x")
    assert store.has("123_x")

    # a fresh instance sees what was persisted
    assert NotifiedStore(path).has("123_x")


def test_corrupt_file_starts_fresh(tmp_path):
    path = tmp_path / "notified.json"
    path.write_text("not json", encoding="utf-8")
    store = NotifiedStore(path)
    assert not store.has("anything")
    store.add("ok")
    assert NotifiedStore(path).has("ok")
