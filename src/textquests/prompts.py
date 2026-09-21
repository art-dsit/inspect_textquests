"""Prompt text, identical to the maintained upstream harness.

Source: https://github.com/centerforaisafety/simple-evals/blob/main/textquests/textquests_eval.py
(get_system_prompt, get_observation_prompt and the game-over block in play_single_game).
The odd indentation of GAME_OVER_FORMAT is upstream's.
"""


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
