"""Episode loop, mirroring play_single_game in the maintained upstream harness.

Source: https://github.com/centerforaisafety/simple-evals/blob/main/textquests/textquests_eval.py

Results accumulate in TextQuestsStore after every step so the scorer still has them if the
sample is cut short by an Inspect limit or an error.
"""

import base64
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import anyio
from inspect_ai.log import transcript
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    Content,
    ContentImage,
    ContentText,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store_as

from textquests.data import ensure_data, load_walkthrough
from textquests.env import (
    PROGRESS_COMPLETE,
    StepResult,
    TextQuestsEnv,
    game_finished,
)
from textquests.prompts import (
    GAME_OVER_FORMAT,
    JSON_GAME_OVER_FORMAT,
    PACKAGE_SCANS_INTRO,
    canonical_response,
    json_canonical_response,
    json_system_prompt,
    observation_prompt,
    system_prompt,
)
from textquests.store import StepLog, TextQuestsStore

DEFAULT_MAX_STEPS = 500
DEFAULT_MAX_RETRIES = 3
DEFAULT_SEED = 1
OutputFormat = Literal["xml", "json"]
DEFAULT_OUTPUT_FORMAT: OutputFormat = "xml"

REASONING_RE = re.compile(r"<reasoning>(.*?)</reasoning>", re.DOTALL | re.IGNORECASE)
ACTION_RE = re.compile(r"<action>(.*?)</action>", re.DOTALL | re.IGNORECASE)


def parse_response(content: str) -> tuple[str, str | None]:
    """Extract (reasoning, action) from the model's XML-tagged reply; action is None if absent."""
    reasoning_match = REASONING_RE.search(content)
    action_match = ACTION_RE.search(content)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
    action = action_match.group(1).strip() if action_match else None
    return reasoning, action


JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def parse_json_response(content: str) -> tuple[Any, str | None]:
    """Extract (reasoning, action) from a JSON reply, as the original harness does.

    Port of extract_json_with_keys in
    https://github.com/centerforaisafety/textquests/blob/18dc472/src/llm_agents.py: the whole
    reply as JSON, else the last ```json block, else the last brace-balanced object. Both
    keys are required. The reasoning is returned as parsed, since that is what the original
    writes back into the history.
    """
    parsed = _extract_json(content)
    if not isinstance(parsed, dict) or not {"reasoning", "action"} <= parsed.keys():
        return "", None
    return parsed["reasoning"], str(parsed["action"])


def _extract_json(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    candidate = None
    if "```json" in content:
        blocks = JSON_BLOCK_RE.findall(content)
        if blocks:
            candidate = blocks[-1]
    if not candidate:
        objects = JSON_OBJECT_RE.findall(content)
        if objects:
            candidate = objects[-1]
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


@solver
def textquests_solver(
    max_steps: int = DEFAULT_MAX_STEPS,
    with_clues: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    canonicalize_history: bool = True,
    output_format: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    verified: bool = False,
) -> Solver:
    """Play one game with the active model.

    Args:
        max_steps: Maximum number of actions per game.
        with_clues: Include the game's InvisiClues hint booklet in the system prompt.
        max_retries: Attempts to get a parseable ``<action>`` before giving up on the game.
        seed: Seed for the Z-machine interpreter's random number generator.
        canonicalize_history: Rewrite each assistant turn in the history to the bare
            ``<reasoning>/<action>`` form, as upstream does. The model's original output is
            still in the transcript. Set False to keep the raw output in the history.
        output_format: Reply format the prompts ask for: "xml" (``<reasoning>/<action>``
            tags, the maintained upstream harness) or "json" (a ``{"reasoning", "action"}``
            block, the original harness that produced the paper's results).
        verified: End the game on the verified 100% checkpoint, not upstream's, whose
            string in several games also prints on a losing ending; and show the model,
            with the first turn, the scanned package items the game cannot be finished
            without.
    """
    if output_format not in ("xml", "json"):
        raise ValueError(
            f"output_format must be 'xml' or 'json', got {output_format!r}"
        )
    as_json = output_format == "json"
    make_system_prompt = json_system_prompt if as_json else system_prompt
    game_over_format = JSON_GAME_OVER_FORMAT if as_json else GAME_OVER_FORMAT
    parse: Callable[[str], tuple[Any, str | None]] = (
        parse_json_response if as_json else parse_response
    )
    canonical: Callable[[Any, str], str] = (
        json_canonical_response if as_json else canonical_response
    )
    if max_steps < 1:
        raise ValueError(f"max_steps must be at least 1, got {max_steps}")
    if max_retries < 1:
        raise ValueError(f"max_retries must be at least 1, got {max_retries}")

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        store = store_as(TextQuestsStore)
        env = await _make_env(state, seed)
        result = env.reset()
        state.messages = [
            ChatMessageSystem(
                content=make_system_prompt(
                    game_name=env.game_name,
                    max_score=env.max_score,
                    guidelines=env.guidelines,
                    invisiclues=env.invisiclues if with_clues else "",
                )
            )
        ]
        model = get_model()
        observation = result.observation
        game_over = False

        for step in range(max_steps):
            if game_over:
                observation += game_over_format
            prompt = observation_prompt(result.score, observation, step)
            if verified and step == 0 and env.package_scans:
                content: list[Content] = [ContentText(text=PACKAGE_SCANS_INTRO)]
                content += [
                    ContentImage(image=_jpeg_data_uri(p)) for p in env.package_scans
                ]
                content.append(ContentText(text=prompt))
                state.messages.append(ChatMessageUser(content=content))
            else:
                state.messages.append(ChatMessageUser(content=prompt))

            parsed = await _get_action(model, state.messages, max_retries, parse)
            if isinstance(parsed, str):
                store.ended = parsed
                break
            reasoning, action, output = parsed
            state.output = output
            if canonicalize_history:
                state.messages.append(
                    ChatMessageAssistant(
                        content=canonical(reasoning, action),
                        model=output.model,
                    )
                )
            else:
                state.messages.append(output.message)

            store.log.append(
                StepLog(
                    step=step,
                    observation=observation,
                    score=result.score,
                    progress=result.progress,
                    game_over=game_over,
                    reasoning=reasoning
                    if isinstance(reasoning, str)
                    else json.dumps(reasoning),
                    action=action,
                    label_vectors=result.label_vectors,
                )
            )
            store.steps = step + 1

            if _finished(env, result, verified):
                store.ended = "finished"
                break

            env.save_checkpoint(observation, result)
            result = env.step(action)
            observation = result.observation
            game_over = result.done
            _record(store, result, env)
        else:
            store.ended = "max_steps"

        return state

    return solve


@solver
def walkthrough_solver(seed: int = DEFAULT_SEED) -> Solver:
    """Oracle: replay the game's bundled walkthrough instead of asking a model."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        store = store_as(TextQuestsStore)
        env = await _make_env(state, seed)
        result = env.reset()
        for step, action in enumerate(load_walkthrough(env.game_name, fixed=True)):
            store.log.append(
                StepLog(
                    step=step,
                    observation=result.observation,
                    score=result.score,
                    progress=result.progress,
                    game_over=result.done,
                    reasoning="",
                    action=action,
                    label_vectors=result.label_vectors,
                )
            )
            store.steps = step + 1
            if game_finished(result.progress, result.score, env.max_score):
                store.ended = "finished"
                break
            env.save_checkpoint(result.observation, result)
            result = env.step(action)
            _record(store, result, env)
        else:
            store.ended = "walkthrough_exhausted"
        return state

    return solve


def _jpeg_data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _finished(env: TextQuestsEnv, result: StepResult, verified: bool) -> bool:
    if verified:
        return (
            PROGRESS_COMPLETE in env.verified_reached or result.score == env.max_score
        )
    return game_finished(result.progress, result.score, env.max_score)


async def _make_env(state: TaskState, seed: int) -> TextQuestsEnv:
    data = await anyio.to_thread.run_sync(ensure_data)
    return TextQuestsEnv(data / str(state.metadata["game"]), seed=seed)


async def _get_action(
    model: Model,
    messages: list[ChatMessage],
    max_retries: int,
    parse: Callable[[str], tuple[Any, str | None]],
) -> tuple[Any, str, ModelOutput] | str:
    """Generate against the unchanged history until the reply contains an action.

    Returns the parsed reply, or the reason the episode has to end.
    """
    for attempt in range(1, max_retries + 1):
        output = await model.generate(messages)
        reasoning, action = parse(output.completion)
        if action is not None:
            return reasoning, action, output
        if output.stop_reason == "model_length":
            transcript().info("History no longer fits the model's context window.")
            return "context_limit"
        transcript().info(
            f"No action in model output (attempt {attempt}/{max_retries}): "
            f"{output.completion[:200]!r}"
        )
    return "parse_failure"


def _record(store: TextQuestsStore, result: StepResult, env: TextQuestsEnv) -> None:
    store.progress = max(store.progress, result.progress)
    store.max_score = max(store.max_score, result.score)
    store.harm += result.harm
    store.checkpoints = sorted(env.checkpoints_reached)
    store.verified_checkpoints = sorted(env.verified_reached)
    store.verified_total = len(set(env.verified_checkpoints.values()))
    store.restores = env.total_restores
    store.restarts = env.total_restarts
