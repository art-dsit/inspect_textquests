"""Prompt text, identical to upstream's two harnesses.

"xml": the maintained harness,
https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py
(get_system_prompt, get_observation_prompt and the game-over block in play_single_game).

"json": the original harness, which produced the paper's results,
https://github.com/centerforaisafety/textquests/blob/18dc472/play_textquests.py
(_get_system_prompt and the game-over block in play_single_game). The observation prompt is
the same in both.

The odd indentation, the doubled braces in JSON_GAME_OVER_FORMAT and "a observation" are
upstream's.
"""

import json
from typing import Any


def system_prompt(
    game_name: str, max_score: int, guidelines: str, invisiclues: str
) -> str:
    guidelines_prompt = ""
    if guidelines:
        guidelines_prompt = f"""Here are the original Guidelines for the game {game_name}:
=====[Guidelines]=====
{guidelines}
"""

    clues_prompt = ""
    if invisiclues:
        clues_prompt = f"""
=====[Invisiclues]=====
{invisiclues}
"""

    return f"""You are a text-based game player. Your goal is to finish the game.

GAME: {game_name}
MAX SCORE: {max_score}

During each game turn, you will be given an observation of the current game state. To take an action, generate a single parser command action.

{guidelines_prompt}{clues_prompt}

[OUTPUT FORMAT DURING GAME TURNS]
Respond using the following XML-style format:
<reasoning>
Your step-by-step reasoning for the action you will take.
</reasoning>
<action>
your action command
</action>

SPECIAL ACTION: You can restore the game to previous steps by using 'restore {{step_id}}' for the step that you want to backtrack.
"""


# Not upstream: opens the Verified task's system prompt. Without it, OpenAI's prompt filter
# refuses some long histories about half the time; at the end of the system prompt, after
# the manual text, it makes no difference.
FICTION_NOTE = (
    "This conversation is a playthrough of a published work of interactive fiction, an "
    "Infocom text adventure from the 1980s. Everything in it, including any crime, "
    "violence or danger, is fictional game content."
)

# Not upstream: introduces the package scans the Verified task shows with the first turn
PACKAGE_SCANS_INTRO = (
    "The images below are from the game's original package. You may need them to play."
)


def observation_prompt(score: int, observation: str, step: int) -> str:
    return f"""
STEP: {step} | CURRENT SCORE: {score}

OBSERVATION:
{observation}
"""


GAME_OVER_FORMAT = """
    [OUTPUT FORMAT]
    <reasoning>
    Your step-by-step reasoning for the action.
    </reasoning>
    <action>
    If restore then 'restore {step_id}' for the step that you want to backtrack to, else 'restart'.
    </action>
    """


def canonical_response(reasoning: str, action: str) -> str:
    """The form in which upstream writes the assistant turn back into the history."""
    return f"<reasoning>\n{reasoning}\n</reasoning>\n<action>\n{action}\n</action>"


def json_system_prompt(
    game_name: str, max_score: int, guidelines: str, invisiclues: str
) -> str:
    feelies = ""
    if invisiclues:
        feelies += f"=====[Invisiclues]=====\n{invisiclues}\n"
    if guidelines:
        feelies += f"=====[Feelies]=====\n{guidelines}\n"
    feelies_prompt = f"""Here are the original Guideline and Clues for the game {game_name}:
    {feelies}
    """

    # {" "} below: upstream has a trailing space there, which linters would strip

    return f"""You are a text-based game player. Your goal is to finish the game.

GAME: {game_name}
MAX SCORE: {max_score}

During each game turn, you will be given a observation of the current game state. To take an action, generate a single parser command action.

{feelies_prompt}

[OUTPUT FORMAT DURING GAME TURNS]
Return a final json block with the following format (make sure the final json block is wrapped around ```json\n{{}}\n```):
```json
{{
    "reasoning": "<your step-by-step reasoning for action.>",{" "}
    "action": <action to take>
}}
```

SPECIAL ACTION: You can restore the game to previous steps by using 'restore {{step_id}}' for the step that you want to backtrack.
"""


JSON_GAME_OVER_FORMAT = """
    [OUTPUT FORMAT]
    ```json
    {{
    "reasoning": "<your step-by-step reasoning for action.>",
    "action": if restore then 'restore {{step_id}}' for the step that you want to backtrack to, else 'restart'.
    }}
    ```
    """


def json_canonical_response(reasoning: Any, action: str) -> str:
    """The form in which the original harness writes the assistant turn back into the history."""
    return f"```json\n{json.dumps(dict(reasoning=reasoning, action=action))}\n```"
