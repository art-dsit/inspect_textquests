"""Replay every bundled walkthrough and compare with the upstream environment.

Expected values were produced by running the same walkthroughs through
centerforaisafety/textquests@18dc472 src/textquests_env.py. Progress, max score and harm
match exactly for all games.
"""

from pathlib import Path

import pytest

from textquests.data import load_walkthrough
from textquests.env import TextQuestsEnv
from textquests.game_info import GAME_INFO, GAMES

# game: (steps until finished, progress, max score, harm)
EXPECTED = {
    "ballyhoo": (363, 100, 200, 46),
    "borderzone": (159, 98, 40, 19),  # stops on max score before the last checkpoint
    "cutthroats": (229, 100, 180, 8),
    "deadline": (144, 100, 17, 0),
    "enchanter": (226, 100, 400, 8),
    "hitchhiker": (378, 100, 410, 27),
    "hollywoodhijinx": (389, 100, 150, 21),
    "infidel": (221, 100, 410, 8),
    "lurkinghorror": (265, 100, 100, 18),
    "moonmist": (122, 10, 1, 0),  # walkthrough doesn't answer the opening name prompt
    "planetfall": (372, 100, 85, 33),
    "plunderedhearts": (184, 100, 25, 31),
    "seastalker": (177, 0, 1, 1),  # walkthrough doesn't answer the opening name prompt
    "sherlock": (319, 100, 99, 24),
    "sorcerer": (254, 100, 400, 14),
    "spellbreaker": (411, 100, 600, 20),
    "starcross": (227, 100, 400, 11),
    "stationfall": (346, 100, 80, 34),
    "suspect": (172, 100, 21, 16),
    "trinity": (576, 100, 100, 47),
    "wishbringer": (195, 100, 100, 15),
    "witness": (82, 100, 14, 2),
    "zork1": (348, 100, 360, 63),
    "zork2": (273, 100, 410, 63),
    "zork3": (276, 100, 8, 11),
}

BROKEN_WALKTHROUGHS = {"moonmist", "seastalker"}


def test_expected_covers_all_games() -> None:
    assert set(EXPECTED) == set(GAMES)


@pytest.mark.slow
@pytest.mark.dataset_download
@pytest.mark.parametrize("game", GAMES)
def test_walkthrough_matches_upstream(data_dir: Path, game: str) -> None:
    env = TextQuestsEnv(data_dir / game)
    result = env.reset()
    max_score = harm = steps = 0
    for action in load_walkthrough(game):
        env.save_checkpoint(result.observation, result)
        result = env.step(action)
        steps += 1
        harm += result.harm
        max_score = max(max_score, result.score)
        if result.progress >= 100 or result.score == env.max_score:
            break
    assert (steps, result.progress, max_score, harm) == EXPECTED[game]
    if game not in BROKEN_WALKTHROUGHS:
        assert result.progress == 100 or max_score == GAME_INFO[game].max_score
