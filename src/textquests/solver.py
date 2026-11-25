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
DEFAULT_SEED = 1
# Kept low: resending a prompt the provider's filter has flagged can count against the account
VERIFIED_REFUSAL_ATTEMPTS = 2
OutputFormat = Literal["xml", "json"]
DEFAULT_OUTPUT_FORMAT: OutputFormat = "xml"
# Each upstream harness's default: the maintained one (tags) 3, the original (JSON) 10
DEFAULT_MAX_RETRIES: dict[OutputFormat, int] = {"xml": 3, "json": 10}

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
    max_retries: int | None = None,
    seed: int = DEFAULT_SEED,
    canonicalize_history: bool = True,
    output_format: OutputFormat = DEFAULT_OUTPUT_FORMAT,
    verified: bool = False,
) -> Solver:
    """Play one game with the active model.

    Args:
        max_steps: Maximum number of actions per game.
        with_clues: Include the game's InvisiClues hint booklet in the system prompt.
        max_retries: Attempts to get a parseable reply before giving up on the game; by
            default 3 for "xml" and 10 for "json", as in the corresponding upstream harness.
        seed: Seed for the Z-machine interpreter's random number generator.
        canonicalize_history: Rewrite each assistant turn in the history to the bare
            ``<reasoning>/<action>`` form, as upstream does. The model's original output is
            still in the transcript. Set False to keep the raw output in the history.
        output_format: Reply format the prompts ask for: "xml" (``<reasoning>/<action>``
            tags, the maintained upstream harness) or "json" (a ``{"reasoning", "action"}``
            block, the original harness that produced the paper's results).
        verified: End the game when it ends after the verified 100% checkpoint, not
            on upstream's, whose string in several games also prints on a losing ending;
            show the model, with the first turn, the scanned package items the game
            cannot be finished without; and play in the corrected environment (see
            `TextQuestsEnv`).
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
    attempts = (
        DEFAULT_MAX_RETRIES[output_format] if max_retries is None else max_retries
    )
    if attempts < 1:
        raise ValueError(f"max_retries must be at least 1, got {attempts}")

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        store = store_as(TextQuestsStore)
        store.verified = verified
        env = await _make_env(state, seed, verified)
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

            parsed = await _get_action(
                model,
                state.messages,
                attempts,
                parse,
                refusal_attempts=VERIFIED_REFUSAL_ATTEMPTS if verified else 0,
            )
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
def walkthrough_solver(seed: int = DEFAULT_SEED, verified: bool = False) -> Solver:
    """Oracle: replay the game's bundled walkthrough instead of asking a model.

    Args:
        seed: Seed for the Z-machine interpreter's random number generator.
        verified: Play in the corrected environment and end the game as
            `textquests_solver(verified=True)` does.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        store = store_as(TextQuestsStore)
        store.verified = verified
        env = await _make_env(state, seed, verified)
        result = env.reset()
        actions = load_walkthrough(env.game_name, fixed=True)
        # One entry more than there are actions: the state after the last one is logged as
        # upstream's loop would log it before asking for another action
        for step, action in enumerate([*actions, ""]):
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
            exhausted = step == len(actions)
            if not exhausted:
                store.steps = step + 1
            if _finished(env, result, verified):
                store.ended = "finished"
                break
            if exhausted:
                store.ended = "walkthrough_exhausted"
                break
            env.save_checkpoint(result.observation, result)
            result = env.step(action)
            _record(store, result, env)
        return state

    return solve


def _jpeg_data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _finished(env: TextQuestsEnv, result: StepResult, verified: bool) -> bool:
    if verified:
        # Several games award their last points after the 100% text, as the game ends
        won = PROGRESS_COMPLETE in env.verified_reached and env.state.game_over
        return won or result.score == env.max_score
    return game_finished(result.progress, result.score, env.max_score)


async def _make_env(state: TaskState, seed: int, verified: bool) -> TextQuestsEnv:
    data = await anyio.to_thread.run_sync(ensure_data)
    return TextQuestsEnv(
        data / str(state.metadata["game"]), seed=seed, verified=verified
    )


async def _get_action(
    model: Model,
    messages: list[ChatMessage],
    max_retries: int,
    parse: Callable[[str], tuple[Any, str | None]],
    refusal_attempts: int = 0,
) -> tuple[Any, str, ModelOutput] | str:
    """Generate against the unchanged history until the reply contains an action.

    Returns the parsed reply, or the reason the episode has to end. With
    ``refusal_attempts``, a reply the provider's content filter refused is not counted
    against ``max_retries`` but against that limit.
    """
    attempt = refusals = 0
    while attempt < max_retries:
        output = await model.generate(messages)
        reasoning, action = parse(output.completion)
        if action is not None:
            return reasoning, action, output
        if output.stop_reason == "model_length":
            transcript().info("History no longer fits the model's context window.")
            return "context_limit"
        if refusal_attempts and output.stop_reason == "content_filter":
            refusals += 1
            transcript().info(
                f"The provider refused the prompt ({refusals}/{refusal_attempts}): "
                f"{output.completion[:200]!r}"
            )
            if refusals == refusal_attempts:
                return "provider_refusal"
            continue
        attempt += 1
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
