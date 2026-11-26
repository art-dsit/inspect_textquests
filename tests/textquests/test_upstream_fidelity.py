"""Replay games through upstream's environment and ours, and compare every step.

Upstream's environment and metric code are vendored in tests/textquests/upstream. Each
sequence is played the way both harness loops play it: reset, then for each action append the
game-over prompt if the previous step ended the game, checkpoint, step. ``restore N`` and
``restart`` are passed through as actions. The sequences are the bundled walkthroughs and the
first 150 actions of each game in two full runs (upstream_trajectories.json; three of them end
at the first file command instead, which comes later or earlier than that).

The only allowed difference is a file command (FILE_COMMANDS in game_info), which our
environment answers "Impossible." and upstream's passes to the interpreter. The two games are
not the same game after that, so a sequence stops at its first one.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from inspect_ai import eval
from inspect_ai.model import ModelOutput, get_model

from tests.textquests.upstream.textquests_env import TextQuestsEnv as UpstreamEnv
from tests.textquests.upstream.textquests_eval_metrics import (
    compute_game_immorality,
    get_game_progress,
)
from textquests.data import load_walkthrough
from textquests.env import RESTORE_RE, StepResult, TextQuestsEnv, game_finished
from textquests.game_info import GAMES, MAX_SCORES
from textquests.prompts import GAME_OVER_FORMAT, canonical_response
from textquests.scorer import upstream_metrics
from textquests.store import StepLog
from textquests.textquests import textquests

pytestmark = pytest.mark.filterwarnings("ignore:Game .* is not fully supported")

# Appended in upstream's play_single_game, simple-evals textquests/textquests_eval.py
UPSTREAM_GAME_OVER_TEXT = """
    [OUTPUT FORMAT]
    <reasoning>
    Your step-by-step reasoning for the action.
    </reasoning>
    <action>
    If restore then 'restore {step_id}' for the step that you want to backtrack to, else 'restart'.
    </action>
    """

FIXTURE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "upstream_trajectories.json").read_text()
)
RUNS = sorted(FIXTURE["trajectories"])
# Sequences that end at a file command, by the action's index
FILE_COMMAND_AT = {
    ("borderzone", "gpt-4.1"): 278,  # a bare "restore"
    ("seastalker", "gpt-4.1"): 82,  # "save"
    ("zork3", "gpt-4.1"): 429,  # "save"
}


def actions_of(game: str, sequence: str) -> list[str]:
    if sequence == "walkthrough":
        return load_walkthrough(game)
    return list(FIXTURE["trajectories"][sequence][game])


def upstream_view(
    env: Any, observation: str, reward: int, done: bool, info: dict[str, Any]
) -> dict[str, Any]:
    return {
        "observation": observation,
        "reward": int(reward),
        "done": bool(done),
        "score": int(info.get("score", 0)),
        "progress": int(info.get("game_progress", 0)),
        "label_vectors": [lv.tolist() for lv in info.get("label_vectors", [])],
        "game_over": env.state["game_over"],
        "restores": env.get_total_restores(),
    }


def our_view(env: TextQuestsEnv, result: StepResult) -> dict[str, Any]:
    return {
        "observation": result.observation,
        "reward": result.reward,
        "done": result.done,
        "score": result.score,
        "progress": result.progress,
        "label_vectors": result.label_vectors,
        "game_over": env.state.game_over,
        "restores": env.total_restores,
    }


def same_interpreter_state(upstream: UpstreamEnv, ours: TextQuestsEnv) -> bool:
    # (ram, stack, pc, sp, fp, frame_count, opcode, rng); the narrative text after them is
    # the last output, which differs once one side answered "Impossible." itself
    a, b = upstream.env.get_state()[:8], ours.frotz.get_state()[:8]
    return all(
        np.array_equal(x, y) if isinstance(x, np.ndarray) else x == y
        for x, y in zip(a, b, strict=True)
    )


def replay(data_dir: Path, game: str, actions: list[str]) -> dict[str, Any]:
    """Play both environments in lockstep; returns what was compared and both step logs."""
    upstream = UpstreamEnv(game_folder_path=str(data_dir / game))
    ours = TextQuestsEnv(data_dir / game)
    u_obs, u_info = upstream.reset()
    o_result = ours.reset()
    o_obs = o_result.observation
    u_view = upstream_view(upstream, u_obs, 0, False, u_info)
    o_view = our_view(ours, o_result)
    assert u_view == o_view
    u_done = o_done = False
    u_log: list[dict[str, Any]] = []
    o_log: list[StepLog] = []
    restarts = 0
    file_command_at = None
    for step, action in enumerate(actions):
        if u_done:
            u_obs += UPSTREAM_GAME_OVER_TEXT
        if o_done:
            o_obs += GAME_OVER_FORMAT
        assert u_obs == o_obs, step
        u_log.append(
            {
                "observation": u_obs,
                "score": u_view["score"],
                "label_vectors": u_view["label_vectors"],
            }
        )
        o_log.append(
            StepLog(
                step=step,
                observation=o_obs,
                score=o_result.score,
                progress=o_result.progress,
                game_over=o_done,
                reasoning="",
                action=action,
                label_vectors=o_result.label_vectors,
            )
        )
        finished = game_finished(o_view["progress"], o_view["score"], ours.max_score)
        assert finished == (
            u_view["progress"] == 100 or u_view["score"] == upstream.get_max_score()
        ), step
        if finished:
            break

        upstream.save_checkpoint(u_obs, u_info)
        ours.save_checkpoint(o_obs, o_result)
        u_obs, u_reward, u_done, u_info = upstream.step(action)
        o_result = ours.step(action)
        o_obs, o_done = o_result.observation, o_result.done
        u_view = upstream_view(upstream, u_obs, u_reward, u_done, u_info)
        o_view = our_view(ours, o_result)

        command = action.lower().strip()
        if not RESTORE_RE.match(command) and "restart" in command:
            restarts += 1
        assert ours.total_restarts == restarts, step
        if o_obs == "Impossible." and u_obs != "Impossible.":
            file_command_at = step
            break
        assert u_view == o_view, (step, action)
        assert same_interpreter_state(upstream, ours), (step, action)
    return {"file_command_at": file_command_at, "upstream_log": u_log, "our_log": o_log}


def assert_same_metrics(data_dir: Path, game: str, played: dict[str, Any]) -> None:
    u_log = played["upstream_log"]
    checkpoints = json.loads((data_dir / "game_progress.json").read_text())
    upstream = (
        get_game_progress(game, [e["observation"] for e in u_log], checkpoints),
        max(e["score"] for e in u_log),
        compute_game_immorality([e["label_vectors"] for e in u_log]),
    )
    assert upstream_metrics(game, played["our_log"]) == upstream


@pytest.mark.dataset_download
@pytest.mark.parametrize("sequence", ["walkthrough", *RUNS])
@pytest.mark.parametrize("game", GAMES)
def test_step_by_step_equal_to_upstream(
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    game: str,
    sequence: str,
) -> None:
    # Upstream lets Frotz's save through, which writes to the cwd
    monkeypatch.chdir(tmp_path)
    actions = actions_of(game, sequence)
    played = replay(data_dir, game, actions)
    expected = FILE_COMMAND_AT.get((game, sequence))
    assert played["file_command_at"] == expected
    if expected is not None:
        assert expected == len(actions) - 1
    assert_same_metrics(data_dir, game, played)


# File commands are blocked in every command of an action. The rest of the blacklist is
# matched as upstream matches it, against the whole action, so these pass through.
FILE_COMMAND_CASES = [
    ("zork1", "save"),
    ("zork1", "look. save"),
    ("zork1", "go restore"),
    ("zork1", "look then script"),
    ("planetfall", "#record"),
    ("planetfall", "look. #random"),
    ("witness", "suspend"),
    ("stationfall", "rescue"),
]
PASSED_THROUGH = [
    ("zork1", "quit."),
    ("zork1", "q "),
    ("zork1", "look. superbrief"),
    ("sherlock", "hint"),
    ("borderzone", "hints"),
]


@pytest.mark.dataset_download
@pytest.mark.parametrize(("game", "action"), FILE_COMMAND_CASES + PASSED_THROUGH)
def test_only_file_commands_differ(
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    game: str,
    action: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    actions = [*load_walkthrough(game)[:3], action]
    played = replay(data_dir, game, [*actions, "look"])
    expected = len(actions) - 1 if (game, action) in FILE_COMMAND_CASES else None
    assert played["file_command_at"] == expected


@pytest.mark.dataset_download
@pytest.mark.parametrize(
    ("game", "sequence"), [("suspect", "gpt-4.1"), ("ballyhoo", "gpt-5")]
)
def test_task_scores_as_upstreams_metric_code(
    data_dir: Path, game: str, sequence: str
) -> None:
    # Progress differs between raw and cleaned text in both: upstream credits 35% on the
    # cleaned text in suspect, and 10% from a marker's object name in ballyhoo
    actions = actions_of(game, sequence)
    played = replay(data_dir, game, actions)
    u_log = played["upstream_log"]
    checkpoints = json.loads((data_dir / "game_progress.json").read_text())
    outputs = [
        ModelOutput.from_content("mockllm/model", canonical_response("", a))
        for a in actions
    ]
    (log,) = eval(
        textquests(games=game, max_steps=len(actions)),
        model=get_model("mockllm/model", custom_outputs=outputs),
        display="none",
        log_dir=None,
    )
    assert log.status == "success", log.error
    assert log.samples and log.samples[0].scores
    value = log.samples[0].scores["textquests_scorer"].value
    assert isinstance(value, dict)
    assert value["progress"] == get_game_progress(
        game, [e["observation"] for e in u_log], checkpoints
    )
    assert value["points"] == 100 * max(e["score"] for e in u_log) / MAX_SCORES[game]
    assert value["harm"] == compute_game_immorality([e["label_vectors"] for e in u_log])
