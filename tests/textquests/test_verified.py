"""The verified checkpoint set: counts, coverage on the walkthroughs, and the audit's replay cases."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from textquests.data import load_walkthrough
from textquests.env import MAX_ACTION_LENGTH, TextQuestsEnv
from textquests.game_info import GAMES, PACKAGE_SCANS
from textquests.solver import _finished
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


# Cases whose outcome the verified environment changes, and why
VERIFIED_MODE_CHANGES = {
    # The game ends at the jump and at 8 pm, so the later action is refused
    "trap-jump-death-not-game-over": "deadline's jump ends the game",
    "trap-8pm-deadline-not-game-over": "deadline's 8 pm time limit ends the game",
    # Tip's line printed after status-line redraws on the same line is kept
    "70-residual-env-strips-report-during-wait": "seastalker's event text is kept",
    # The text the game prints after the player's death is cut
    "30-fires-although-player-shot-dead": "witness's death in the shot ends the game",
}


@pytest.mark.dataset_download
@pytest.mark.parametrize("verified", [False, True], ids=["default", "verified"])
@pytest.mark.parametrize("game", GAMES)
def test_audit_cases(data_dir: Path, game: str, verified: bool) -> None:
    """Replay cases from the audit: where each original and replacement string does and does not occur."""
    cases = [case for case in CASES if case["game"] == game]
    assert cases
    assert set(VERIFIED_MODE_CHANGES) <= {case["name"] for case in CASES}
    walkthrough = load_walkthrough(game)
    for case in cases:
        env = TextQuestsEnv(data_dir / game, verified=verified)
        env.reset()
        setup = case["setup"]
        prefix = setup.get("actions", walkthrough[: setup.get("walkthrough_upto", 0)])
        for action in prefix:
            env.step(action)
        seen = False
        for action in case["actions"]:
            observation = env.step(action).observation.lower()
            seen = seen or any(s.lower() in observation for s in case["strings"])
        expect = case["expect"]
        if verified and case["name"] in VERIFIED_MODE_CHANGES:
            expect = not expect
        assert seen == expect, case["name"]


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


@pytest.mark.dataset_download
def test_package_scans_exist_in_the_data(data_dir: Path) -> None:
    for game in PACKAGE_SCANS:
        scans = TextQuestsEnv(data_dir / game).package_scans
        assert scans and all(scan.is_file() for scan in scans), game


STATUS_LINE_RE = re.compile(r"Time: +\d{1,2}:\d\d|Score: +-?\d+ +Moves: +\d+")


@pytest.mark.dataset_download
@pytest.mark.parametrize("game", GAMES)
def test_verified_oracle_finishes_with_every_checkpoint_and_full_points(
    data_dir: Path, game: str
) -> None:
    # As walkthrough_solver(verified=True) plays it
    env = TextQuestsEnv(data_dir / game, verified=True)
    result = env.reset()
    best_score = 0
    for action in load_walkthrough(game, fixed=True):
        if _finished(env, result, verified=True):
            break
        env.save_checkpoint(result.observation, result)
        result = env.step(action)
        best_score = max(best_score, result.score)
        assert not STATUS_LINE_RE.search(result.observation), action
    assert env.verified_reached == set(env.verified_checkpoints.values())
    assert best_score == env.max_score
    assert env.state.game_over, "the walkthrough's last action ends the game"
