from app.slides import SlideLibrary


def test_starts_empty_without_file(tmp_path):
    lib = SlideLibrary(tmp_path / "slides.json")
    assert lib.list() == []


def test_add_assigns_incrementing_ids_and_persists(tmp_path):
    path = tmp_path / "slides.json"
    lib = SlideLibrary(path)
    a = lib.add("Bienvenidos", "Anuncios")
    b = lib.add("Ofrenda", "")
    assert a == {"id": 1, "text": "Bienvenidos", "caption": "Anuncios"}
    assert b["id"] == 2
    reloaded = SlideLibrary(path)
    assert reloaded.list() == [a, b]


def test_update_existing_and_missing(tmp_path):
    path = tmp_path / "slides.json"
    lib = SlideLibrary(path)
    slide = lib.add("Bienvenidos", "")
    updated = lib.update(slide["id"], "Bienvenida", "Iglesia")
    assert updated == {"id": 1, "text": "Bienvenida", "caption": "Iglesia"}
    assert SlideLibrary(path).list() == [updated]
    assert lib.update(99, "x", "") is None


def test_delete_existing_and_missing(tmp_path):
    path = tmp_path / "slides.json"
    lib = SlideLibrary(path)
    slide = lib.add("Bienvenidos", "")
    assert lib.delete(slide["id"]) is True
    assert lib.delete(slide["id"]) is False
    assert SlideLibrary(path).list() == []


def test_corrupt_file_is_backed_up_and_starts_empty(tmp_path):
    path = tmp_path / "slides.json"
    path.write_text("{esto no es json", encoding="utf-8")
    lib = SlideLibrary(path)
    assert lib.list() == []
    assert (tmp_path / "slides.json.bak").exists()
    assert not path.exists()


def test_list_returns_copies(tmp_path):
    lib = SlideLibrary(tmp_path / "slides.json")
    lib.add("Bienvenidos", "")
    lib.list()[0]["text"] = "mutado"
    assert lib.list()[0]["text"] == "Bienvenidos"
