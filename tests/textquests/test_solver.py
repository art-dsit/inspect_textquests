from typing import Any

import pytest
from inspect_ai import eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import ModelOutput, get_model

from textquests.game_info import MAX_SCORES
from textquests.prompts import GAME_OVER_FORMAT, canonical_response
from textquests.solver import parse_response
from textquests.store import TextQuestsStore
from textquests.textquests import textquests

MOCK_MODEL = "mockllm/model"


def test_parse_response() -> None:
    assert parse_response(
        "<reasoning>think</reasoning>\n<action>go north</action>"
    ) == (
        "think",
        "go north",
    )
    assert parse_response("<REASONING>a</REASONING><Action>\n  look \n</Action>") == (
        "a",
        "look",
    )
    assert parse_response("Sure! <action>open mailbox</action> hope that helps") == (
        "",
        "open mailbox",
    )
    assert parse_response("<reasoning>multi\nline</reasoning><action>x</action>") == (
        "multi\nline",
        "x",
    )
    assert parse_response("I will go north.") == ("", None)
    assert parse_response("<action>unterminated") == ("", None)


def turn(action: str, reasoning: str = "because") -> ModelOutput:
    return ModelOutput.from_content(MOCK_MODEL, canonical_response(reasoning, action))


def run(actions: list[ModelOutput], **task_args: Any) -> EvalLog:
    (log,) = eval(
        textquests(games="zork1", **task_args),
        model=get_model(MOCK_MODEL, custom_outputs=actions),
        display="none",
        log_dir=None,
    )
    assert log.status == "success", log.error
    return log


def first_sample(log: EvalLog) -> EvalSample:
    assert log.samples
    return log.samples[0]


def score_value(sample: EvalSample) -> dict[str, Any]:
    assert sample.scores
    value = sample.scores["textquests_scorer"].value
    assert isinstance(value, dict)
    return value


@pytest.mark.dataset_download
def test_episode_with_restore_and_restart() -> None:
    actions = [
        "north",
        "east",
        "open window",
        "west",
        "restore 1",
        "quit",
        "restart",
        "look",
    ]
    log = run([turn(a) for a in actions], max_steps=len(actions))
    sample = first_sample(log)
    store = sample.store_as(TextQuestsStore)

    assert store.steps == len(actions)
    assert store.ended == "max_steps"
    assert store.progress == 5 and store.max_score == 10
    assert store.restores == 1 and store.restarts == 1
    assert score_value(sample) == {
        "progress": 5,
        "points": 100 * 10 / MAX_SCORES["zork1"],
        "harm": store.harm,
        "finished": 0.0,
        "steps": 8,
        "restores": 1,
    }

    observations = [entry.observation for entry in store.log]
    assert observations[0].startswith("ZORK I")
    assert observations[4].startswith("Kitchen")
    # "restore 1" rewinds to the state before the action taken at step 1, i.e. after "north"
    assert observations[5] == observations[1]
    assert observations[5].startswith("North of House")
    assert observations[6] == "Impossible."
    assert observations[7].startswith("ZORK I")
    assert [entry.action for entry in store.log] == actions

    # Conversation is system prompt + (user, assistant) per step, assistant turns canonical
    messages = sample.messages
    assert messages[0].role == "system"
    assert "GAME: zork1" in messages[0].text
    assert "=====[Guidelines]=====" in messages[0].text
    assert "=====[Invisiclues]=====" not in messages[0].text
    assert len(messages) == 1 + 2 * len(actions)
    assert messages[1].text.startswith("\nSTEP: 0 | CURRENT SCORE: 0\n\nOBSERVATION:\n")
    assert messages[9].text.startswith("\nSTEP: 4 | CURRENT SCORE: 10\n")
    assert messages[2].text == canonical_response("because", "north")

    assert log.results is not None
    # dict-valued scores are reported as one result per key, all attributed to the scorer
    results = {s.name: s for s in log.results.scores}
    assert results["progress"].scorer == "textquests_scorer"
    assert results["progress"].metrics["mean"].value == 5
    assert results["harm"].metrics["mean"].value == store.harm


@pytest.mark.dataset_download
def test_with_clues_and_raw_history() -> None:
    log = run([turn("look")], max_steps=1, with_clues=True, canonicalize_history=False)
    messages = first_sample(log).messages
    assert "=====[Invisiclues]=====" in messages[0].text
    assert messages[2].role == "assistant"


@pytest.mark.dataset_download
def test_game_over_prompt_appended_after_death() -> None:
    death = [
        "north",
        "east",
        "open window",
        "west",
        "west",
        "move rug",
        "open trap door",
        "down",
        "north",
    ]
    log = run([turn(a) for a in death + ["restore 8"]], max_steps=len(death) + 1)
    store = first_sample(log).store_as(TextQuestsStore)
    assert "You have died" in store.log[9].observation
    assert store.log[9].observation.endswith(GAME_OVER_FORMAT)
    assert store.log[9].game_over is True
    assert store.max_score == 35, "max score is kept even though death costs points"


@pytest.mark.dataset_download
def test_parse_failure_retries_then_ends_episode() -> None:
    junk = ModelOutput.from_content(MOCK_MODEL, "I don't know what to do.")
    log = run(
        [turn("north"), junk, junk, junk, turn("east")], max_steps=5, max_retries=3
    )
    sample = first_sample(log)
    store = sample.store_as(TextQuestsStore)
    assert store.steps == 1
    assert store.ended == "parse_failure"
    # system, user, assistant, then the user turn whose reply never parsed
    assert len(sample.messages) == 4, "failed attempts are not added to the history"
    assert score_value(sample)["steps"] == 1


@pytest.mark.dataset_download
def test_message_limit_still_scores_partial_run() -> None:
    actions = ["north", "east", "open window", "west", "west", "west"]
    (log,) = eval(
        textquests(games="zork1", max_steps=len(actions)),
        model=get_model(MOCK_MODEL, custom_outputs=[turn(a) for a in actions]),
        message_limit=7,
        display="none",
        log_dir=None,
    )
    assert log.status == "success"
    sample = first_sample(log)
    assert sample.limit is not None and sample.limit.type == "message"
    value = score_value(sample)
    assert value["steps"] >= 3
    assert value["progress"] in (0, 5)
    store = sample.store_as(TextQuestsStore)
    assert store.ended == "", "the solver was interrupted, not completed"


@pytest.mark.dataset_download
def test_walkthrough_solver() -> None:
    from inspect_ai import Task

    from textquests.scorer import textquests_scorer
    from textquests.solver import walkthrough_solver
    from textquests.textquests import games_dataset

    (log,) = eval(
        Task(
            dataset=games_dataset("witness"),
            solver=walkthrough_solver(),
            scorer=textquests_scorer(),
        ),
        model=get_model(MOCK_MODEL),
        display="none",
        log_dir=None,
    )
    assert log.status == "success"
    assert score_value(first_sample(log)) == {
        "progress": 100,
        "points": 100.0,
        "harm": 2,
        "finished": 1.0,
        "steps": 82,
        "restores": 0,
    }
