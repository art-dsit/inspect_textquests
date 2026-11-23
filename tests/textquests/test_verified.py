"""The verified checkpoint set: counts, coverage on the walkthroughs, and the audit's replay cases."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from textquests.data import load_walkthrough
from textquests.env import MAX_ACTION_LENGTH, TextQuestsEnv
from textquests.game_info import GAMES
from textquests.verified import DROPPED, REPLACEMENTS

CASES: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "verified_cases.json").read_text()
)


@pytest.mark.dataset_download
def test_verified_set_matches_the_checkpoint_file(data_dir: Path) -> None:
    assert set(DROPPED) | set(REPLACEMENTS) <= set(GAMES)
    total = zero = verified = 0
    for game in GAMES:
        env = TextQuestsEnv(data_dir / game)
        percentages = list(env.progress_checkpoints.values())
        assert DROPPED.get(game, frozenset()) <= set(percentages), game
        assert set(REPLACEMENTS.get(game, {})) <= set(percentages), game
        assert not DROPPED.get(game, frozenset()) & set(REPLACEMENTS.get(game, {})), (
            game
        )
        total += len(percentages)
        zero += percentages.count(0)
        verified += len(set(env.verified_checkpoints.values()))
    assert (total, zero, sum(map(len, DROPPED.values())), verified) == (327, 8, 9, 310)


@pytest.mark.dataset_download
@pytest.mark.parametrize("game", GAMES)
def test_walkthrough_reaches_every_verified_checkpoint(
    data_dir: Path, game: str
) -> None:
    env = TextQuestsEnv(data_dir / game)
    env.reset()
    for action in load_walkthrough(game, fixed=True):
        env.step(action)
    assert env.verified_reached == set(env.verified_checkpoints.values())


@pytest.mark.dataset_download
@pytest.mark.parametrize("game", GAMES)
def test_typing_a_checkpoint_string_does_not_score_it(
    data_dir: Path, game: str
) -> None:
    # The parser answers "You can't see any <words> here", quoting the player
    env = TextQuestsEnv(data_dir / game)
    for string in env.verified_checkpoints:
        if "\n" in string:
            continue
        words = re.sub(r"[^a-z0-9' -]", " ", string).strip()
        for verb in ("examine", "take", "ask about", "find"):
            action = f"{verb} {words}"
            if len(action) > MAX_ACTION_LENGTH:
                continue
            env.reset()
            env.step("look")  # some games swallow the first input
            assert string not in env.step(action).observation.lower(), action


@pytest.mark.dataset_download
@pytest.mark.parametrize("game", GAMES)
def test_audit_cases(data_dir: Path, game: str) -> None:
    """Replay cases from the audit: where each original and replacement string does and does not occur."""
    cases = [case for case in CASES if case["game"] == game]
    assert cases
    walkthrough = load_walkthrough(game)
    for case in cases:
        env = TextQuestsEnv(data_dir / game)
        env.reset()
        setup = case["setup"]
        prefix = setup.get("actions", walkthrough[: setup.get("walkthrough_upto", 0)])
        for action in prefix:
            env.step(action)
        seen = False
        for action in case["actions"]:
            observation = env.step(action).observation.lower()
            seen = seen or any(s.lower() in observation for s in case["strings"])
        assert seen == case["expect"], case["name"]


@pytest.mark.dataset_download
@pytest.mark.parametrize(
    ("game", "action"),
    [
        ("planetfall", "#record"),
        ("planetfall", "look. #command"),
        ("planetfall", "WAIT. SUPERBRIEF"),
        ("zork1", "look then superbrief"),
        ("zork1", "quit."),
        ("zork1", "q "),
        ("zork1", "go save"),
        ("witness", "suspend"),
        ("witness", "continue"),
        ("stationfall", "rescue"),
        ("sherlock", "hint"),
        ("borderzone", "hints"),
    ],
)
def test_file_and_mode_commands_are_blocked(
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    game: str,
    action: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    env = TextQuestsEnv(data_dir / game)
    env.reset()
    env.step("look")
    assert env.step(action).observation == "Impossible."
    assert list(tmp_path.iterdir()) == []
