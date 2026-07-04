import pytest

from app.fetch_bible import SOURCE_NAME_FIXES, convert_chapters


def test_convert_chapters_orders_and_strips():
    raw = {"2": {"1": "c "}, "1": {"2": " b", "1": " a "}}
    assert convert_chapters("X", 2, raw) == [["a", "b"], ["c"]]


def test_convert_chapters_missing_chapter():
    with pytest.raises(ValueError, match="X"):
        convert_chapters("X", 2, {"1": {"1": "a"}})


def test_convert_chapters_missing_verse():
    with pytest.raises(ValueError, match="X 1"):
        convert_chapters("X", 1, {"1": {"1": "a", "3": "c"}})


def test_convert_chapters_empty_verse():
    with pytest.raises(ValueError, match="X 1"):
        convert_chapters("X", 1, {"1": {"1": "   "}})


def test_gospel_name_fixes():
    assert SOURCE_NAME_FIXES == {
        "S. Mateo": "Mateo",
        "S. Marcos": "Marcos",
        "S. Lucas": "Lucas",
        "S.Juan": "Juan",
    }
