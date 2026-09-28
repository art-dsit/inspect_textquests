"""Episode loop, mirroring play_single_game in the maintained upstream harness.

Source: https://github.com/centerforaisafety/simple-evals/blob/main/textquests/textquests_eval.py

Results accumulate in TextQuestsStore after every step so the scorer still has them if the
sample is cut short by an Inspect limit or an error.
"""

import re

import anyio
from inspect_ai.log import transcript
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store_as

from textquests.data import ensure_data, load_walkthrough
from textquests.env import StepResult, TextQuestsEnv, game_finished
from textquests.prompts import (
    GAME_OVER_FORMAT,
    canonical_response,
    observation_prompt,
    system_prompt,
)
from textquests.store import StepLog, TextQuestsStore

DEFAULT_MAX_STEPS = 500
DEFAULT_MAX_RETRIES = 3
DEFAULT_SEED = 1

REASONING_RE = re.compile(r"<reasoning>(.*?)</reasoning>", re.DOTALL | re.IGNORECASE)
ACTION_RE = re.compile(r"<action>(.*?)</action>", re.DOTALL | re.IGNORECASE)


def parse_response(content: str) -> tuple[str, str | None]:
    """Extract (reasoning, action) from the model's XML-tagged reply; action is None if absent."""
    reasoning_match = REASONING_RE.search(content)
    action_match = ACTION_RE.search(content)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
    action = action_match.group(1).strip() if action_match else None
    return reasoning, action


@solver
def textquests_solver(
    max_steps: int = DEFAULT_MAX_STEPS,
    with_clues: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    canonicalize_history: bool = True,
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
    """
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
                content=system_prompt(
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
                observation += GAME_OVER_FORMAT
            state.messages.append(
                ChatMessageUser(
                    content=observation_prompt(result.score, observation, step)
                )
            )

            parsed = await _get_action(model, state.messages, max_retries)
            if parsed is None:
                store.ended = "parse_failure"
                break
            reasoning, action, output = parsed
            state.output = output
            if canonicalize_history:
                state.messages.append(
                    ChatMessageAssistant(
                        content=canonical_response(reasoning, action),
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
                    reasoning=reasoning,
                    action=action,
                    label_vectors=result.label_vectors,
                )
            )
            store.steps = step + 1

            if game_finished(result.progress, result.score, env.max_score):
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
        for step, action in enumerate(load_walkthrough(env.game_name)):
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


async def _make_env(state: TaskState, seed: int) -> TextQuestsEnv:
    data = await anyio.to_thread.run_sync(ensure_data)
    return TextQuestsEnv(data / str(state.metadata["game"]), seed=seed)


async def _get_action(
    model: Model, messages: list[ChatMessage], max_retries: int
) -> tuple[str, str, ModelOutput] | None:
    """Generate against the unchanged history until the reply contains an <action>."""
    for attempt in range(1, max_retries + 1):
        output = await model.generate(messages)
        reasoning, action = parse_response(output.completion)
        if action is not None:
            return reasoning, action, output
        transcript().info(
            f"No <action> tag in model output (attempt {attempt}/{max_retries}): "
            f"{output.completion[:200]!r}"
        )
    return None


def _record(store: TextQuestsStore, result: StepResult, env: TextQuestsEnv) -> None:
    store.progress = max(store.progress, result.progress)
    store.max_score = max(store.max_score, result.score)
    store.harm += result.harm
    store.restores = env.total_restores
    store.restarts = env.total_restarts
