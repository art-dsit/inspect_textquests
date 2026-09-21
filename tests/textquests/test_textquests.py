import pytest

from textquests import data
from textquests.game_info import GAMES
from textquests.textquests import (
    EVAL_VERSION,
    games_dataset,
    textquests,
    textquests_walkthrough,
)


def test_games_dataset() -> None:
    assert len(games_dataset()) == 25
    assert [s.id for s in games_dataset()] == GAMES
    assert [s.id for s in games_dataset("zork1")] == ["zork1"]
    assert [s.id for s in games_dataset(["zork2", "zork1"])] == ["zork2", "zork1"]
    with pytest.raises(ValueError, match="nope"):
        games_dataset(["zork1", "nope"])


def test_task_construction_needs_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise AssertionError("data must not be downloaded at task-construction time")

    monkeypatch.setattr(data, "ensure_data", boom)
    task = textquests()
    assert len(task.dataset) == 25
    assert task.version == EVAL_VERSION
    assert task.metadata == {"with_clues": False, "max_steps": 500}
    assert len(textquests_walkthrough(games="zork1").dataset) == 1


def test_invalid_parameters_rejected() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        textquests(max_steps=0)
    with pytest.raises(ValueError, match="max_retries"):
        textquests(max_retries=0)
