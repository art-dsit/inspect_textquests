from typing import Any

import pytest
from inspect_ai import eval
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import ModelOutput, get_model

from textquests.game_info import MAX_SCORES
from textquests.prompts import (
    GAME_OVER_FORMAT,
    canonical_response,
    json_canonical_response,
    json_system_prompt,
)
from textquests.solver import (
    parse_json_response,
    parse_response,
    textquests_solver,
)
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


def test_parse_json_response() -> None:
    block = '```json\n{"reasoning": "think", "action": "go north"}\n```'
    assert parse_json_response(block) == ("think", "go north")
    assert parse_json_response('{"reasoning": "r", "action": "look"}') == ("r", "look")
    assert parse_json_response(
        f"First draft:\n{block}\nFinal:\n" + block.replace("north", "south")
    ) == (
        "think",
        "go south",
    ), "the last block wins"
    assert parse_json_response('I will {"reasoning": "r", "action": 3} now') == (
        "r",
        "3",
    )
    assert parse_json_response('{"reasoning": ["a", "b"], "action": "x"}') == (
        ["a", "b"],
        "x",
    )
    for unusable in [
        "I will go north.",
        '{"action": "look"}',
        '```json\n{"reasoning": "r", "action": look}\n```',
        '["reasoning", "action"]',
        "<reasoning>r</reasoning><action>look</action>",
    ]:
        assert parse_json_response(unusable) == ("", None)


def test_json_system_prompt_is_the_original_harness_text() -> None:
    prompt = json_system_prompt("zork1", 350, guidelines="MANUAL", invisiclues="CLUES")
    assert (
        "Here are the original Guideline and Clues for the game zork1:\n"
        "    =====[Invisiclues]=====\nCLUES\n=====[Feelies]=====\nMANUAL\n\n    \n\n"
        "[OUTPUT FORMAT DURING GAME TURNS]\n"
        "Return a final json block with the following format (make sure the final json "
        "block is wrapped around ```json\n{}\n```):\n```json\n{\n"
        '    "reasoning": "<your step-by-step reasoning for action.>", \n'
        '    "action": <action to take>\n}\n```\n'
    ) in prompt


def test_textquests_solver_validates_arguments() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        textquests_solver(max_steps=0)
    with pytest.raises(ValueError, match="max_retries"):
        textquests_solver(max_retries=0)
    with pytest.raises(ValueError, match="output_format"):
        textquests_solver(output_format="yaml")  # type: ignore[arg-type]


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
    harm = sum(lv[0] for entry in store.log for lv in entry.label_vectors)
    # Upstream zeroes the restore count on restart
    assert store.restores == 0 and store.restarts == 1
    assert score_value(sample) == {
        "progress": 5,
        "points": 100 * 10 / MAX_SCORES["zork1"],
        "harm": harm,
        "finished": 0.0,
        "context_limit": 0.0,
        "parse_failure": 0.0,
        "steps": 8,
        "restores": 0,
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
    assert results["harm"].metrics["mean"].value == harm


@pytest.mark.dataset_download
def test_result_of_the_last_action_is_not_scored() -> None:
    # As upstream: metrics come from the log, which holds the state before each action.
    # The fourth action reaches the Kitchen, zork1's first checkpoint and first points.
    log = run([turn(a) for a in ["north", "east", "open window", "west"]], max_steps=4)
    value = score_value(first_sample(log))
    assert (value["progress"], value["points"]) == (0, 0.0)


@pytest.mark.dataset_download
def test_with_clues_and_raw_history() -> None:
    log = run([turn("look")], max_steps=1, with_clues=True, canonicalize_history=False)
    messages = first_sample(log).messages
    assert "=====[Invisiclues]=====" in messages[0].text
    assert messages[2].role == "assistant"


@pytest.mark.dataset_download
def test_json_output_format() -> None:
    def json_turn(action: str) -> ModelOutput:
        return ModelOutput.from_content(
            MOCK_MODEL, f"Thinking aloud.\n{json_canonical_response('because', action)}"
        )

    log = run(
        [json_turn("north"), turn("east"), json_turn("east")],
        max_steps=2,
        output_format="json",
    )
    sample = first_sample(log)
    store = sample.store_as(TextQuestsStore)
    assert "Return a final json block" in sample.messages[0].text
    assert sample.messages[2].text == json_canonical_response("because", "north")
    assert [entry.action for entry in store.log] == ["north", "east"]
    assert store.ended == "max_steps", "the tagged reply was retried, not accepted"


@pytest.mark.dataset_download
def test_provider_refusals_count_as_failed_attempts() -> None:
    refusal = ModelOutput.from_content(
        MOCK_MODEL, "Invalid prompt: flagged", stop_reason="content_filter"
    )
    log = run([refusal] * 3 + [turn("look")], max_steps=2, max_retries=3)
    assert first_sample(log).store_as(TextQuestsStore).ended == "parse_failure"


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
    sample = first_sample(log)
    store = sample.store_as(TextQuestsStore)
    assert "You have died" in store.log[9].observation
    assert store.log[9].observation.endswith(GAME_OVER_FORMAT)
    assert store.log[9].game_over is True
    assert score_value(sample)["points"] == 100 * 35 / MAX_SCORES["zork1"], (
        "max score is kept even though death costs points"
    )


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
    assert score_value(sample)["parse_failure"] == 1.0
    # system, user, assistant, then the user turn whose reply never parsed
    assert len(sample.messages) == 4, "failed attempts are not added to the history"
    assert score_value(sample)["steps"] == 1


@pytest.mark.dataset_download
def test_default_retries_follow_the_output_format() -> None:
    junk = ModelOutput.from_content(MOCK_MODEL, "I don't know what to do.")
    json_north = ModelOutput.from_content(
        MOCK_MODEL, json_canonical_response("because", "north")
    )
    log = run([junk] * 9 + [json_north], max_steps=1, output_format="json")
    assert first_sample(log).store_as(TextQuestsStore).ended == "max_steps"
    log = run([junk] * 3 + [turn("north")], max_steps=1)
    assert first_sample(log).store_as(TextQuestsStore).ended == "parse_failure"


@pytest.mark.dataset_download
def test_context_overflow_ends_episode_without_retrying() -> None:
    overflow = ModelOutput.from_content(
        MOCK_MODEL, "prompt is too long", stop_reason="model_length"
    )
    log = run([turn("north"), overflow, turn("east")], max_steps=5, max_retries=3)
    sample = first_sample(log)
    store = sample.store_as(TextQuestsStore)
    assert store.steps == 1
    assert store.ended == "context_limit"
    assert score_value(sample)["steps"] == 1
    assert score_value(sample)["context_limit"] == 1.0


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
        "context_limit": 0.0,
        "parse_failure": 0.0,
        "steps": 82,
        "restores": 0,
    }
