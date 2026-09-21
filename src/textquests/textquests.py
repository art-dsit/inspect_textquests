"""TextQuests: How Good are LLMs at Text-Based Video Games?

Long Phan, Mantas Mazeika, Andy Zou, Dan Hendrycks. https://arxiv.org/abs/2507.23701

Follows the maintained upstream harness at
https://github.com/centerforaisafety/simple-evals/tree/main/textquests.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from textquests.game_info import GAMES, MAX_SCORES
from textquests.scorer import textquests_scorer
from textquests.solver import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_STEPS,
    DEFAULT_SEED,
    textquests_solver,
    walkthrough_solver,
)
from utils.metadata import load_version_from_yaml

EVAL_VERSION = load_version_from_yaml("textquests")


def games_dataset(games: str | list[str] | None = None) -> MemoryDataset:
    """One sample per game.

    The model's conversation is built by the solver, so the sample input is only a label.
    """
    if games is None:
        selected = GAMES
    else:
        selected = [games] if isinstance(games, str) else list(games)
        unknown = sorted(set(selected) - set(GAMES))
        if unknown:
            raise ValueError(f"Unknown game(s) {unknown}; choose from {GAMES}")
    return MemoryDataset(
        [
            Sample(
                input=f"Play the Infocom game {game}.",
                id=game,
                metadata={"game": game, "max_score": MAX_SCORES[game]},
            )
            for game in selected
        ],
        name="textquests",
    )


@task
def textquests(
    games: str | list[str] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    with_clues: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    canonicalize_history: bool = True,
) -> Task:
    """TextQuests benchmark.

    Args:
        games: Game name or list of game names to run; all 25 by default.
        max_steps: Maximum number of actions per game (upstream default 500).
        with_clues: Include the official InvisiClues hint booklet in the system prompt
            (the "with clues" leaderboard setting). Off by default.
        max_retries: Attempts to get a parseable <action> before abandoning the game.
        seed: Z-machine random seed (upstream uses 1).
        canonicalize_history: Rewrite assistant turns to bare <reasoning>/<action> text in the
            history, as upstream does. Set False to keep the raw model output.
    """
    return Task(
        dataset=games_dataset(games),
        solver=textquests_solver(
            max_steps=max_steps,
            with_clues=with_clues,
            max_retries=max_retries,
            seed=seed,
            canonicalize_history=canonicalize_history,
        ),
        scorer=textquests_scorer(),
        version=EVAL_VERSION,
        metadata={"with_clues": with_clues, "max_steps": max_steps},
    )


@task
def textquests_walkthrough(
    games: str | list[str] | None = None,
    seed: int = DEFAULT_SEED,
) -> Task:
    """Oracle task: replays each game's bundled walkthrough. No model calls.

    Args:
        games: Game name or list of game names to run; all 25 by default.
        seed: Z-machine random seed (upstream uses 1).
    """
    return Task(
        dataset=games_dataset(games),
        solver=walkthrough_solver(seed=seed),
        scorer=textquests_scorer(),
        version=EVAL_VERSION,
    )
