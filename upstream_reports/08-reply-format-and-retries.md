# 08. The maintained harness asks for tags and allows 3 attempts per turn; the paper's results used JSON and 10, so the two do not give comparable results

## Where

- [centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`, `textquests/textquests_eval.py`:
  - [lines 100–108](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L100-L108): the reply format, `<reasoning>` and `<action>` tags.
  - [lines 193–217](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L193-L217): the attempts per turn; a reply without `<action>` and any exception from the API call each use one, and the game ends when they run out.
  - [line 436](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L436): `--max_retries` defaults to 3.
- [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472`, `play_textquests.py`:
  - [line 36](https://github.com/centerforaisafety/textquests/blob/18dc472/play_textquests.py#L36): the reply format, a fenced `json` block with `reasoning` and `action`.
  - [lines 146–168](https://github.com/centerforaisafety/textquests/blob/18dc472/play_textquests.py#L146-L168) and [line 238](https://github.com/centerforaisafety/textquests/blob/18dc472/play_textquests.py#L238): the same retry loop, with `max_retries` 10.

## What happens

The paper ([arXiv 2507.23701](https://arxiv.org/abs/2507.23701), v1 of 31 July 2025, v3 of 13 August 2025) gives the system prompt with the JSON format, and its results predate the maintained harness: `textquests/` was first committed to simple-evals on 2025-11-14. The maintained harness changes two things that decide when a game ends early: the reply format and the number of attempts. A turn on which the model gives 3 replies without an `<action>` tag, or the API call raises 3 times (for example when a provider's prompt filter refuses the history), ends the game, and the game is scored on the turns before it as if it had played to the end (report 02). The original harness allows 10 attempts. Neither harness tells the model that its reply could not be parsed: the same history is sent again.

The format changes how often a model fails to give an action. GPT-5, called through OpenAI's Responses API at high reasoning effort, sometimes replies with the bare word `analysis` alone when asked for tags.

## Reproduce

These numbers need model calls, so they are given as measured. The four histories below are model calls at which GPT-5 replied `analysis` in a run with the tag format (numbered by call within the game); each was sent again 25 times to `gpt-5-2025-08-07` at reasoning effort high.

| History (game, call) | Tags, Responses API | Tags, Chat Completions API | JSON, Responses API |
| :------------------- | :------------------ | :------------------------- | :------------------ |
| zork1, 74            | 24 of 25 parseable  | 25 of 25                   | 25 of 25            |
| planetfall, 264      | 17 of 25            | 25 of 25                   | 25 of 25            |
| zork3, 252           | 25 of 25            | 25 of 25                   | 25 of 25            |
| starcross, 187       | 23 of 25            | 25 of 25                   | 25 of 25            |

The JSON column is the same histories with the tag instructions replaced by the original harness's JSON instructions. simple-evals calls OpenAI models through Chat Completions (`shared/llm_agents.py`), under which these replays did not give a bare `analysis` reply; the Responses API is the default of other clients, Inspect among them, for these models.

## Effect on results

- In a run of GPT-5 (`gpt-5-2025-08-07`, reasoning effort high, 25 games, 500 steps) with the tag format, 3 attempts and the Responses API, made with an Inspect port that plays as the maintained harness does, 9 of 25 games ended early: 7 after three bare `analysis` replies on one turn (zork1 at turn 74, borderzone 184, planetfall 264, zork3 252, lurkinghorror 302, hollywoodhijinx 352, cutthroats 441) and 2 after a mix of such replies and prompt-filter refusals (sorcerer 197, wishbringer 290). Bare replies were rare in the first 50 turns (0 of 1,250 calls) and most frequent between turns 250 and 350 (26 of 1,941 calls).
- Upstream's `evaluate_results` computation over that run's logged observations gives a mean progress of 38.0. A run of the same model with the JSON format and 10 attempts, in which every game played 500 steps, gave 36.8; the paper reports 37.8. The averages are close, but 9 of the tag-format games were scored on fewer than 500 steps, so per-game results and the leaderboard's numbers are not comparable across the two harnesses.

## Suggested fix

- State in the README and on the leaderboard ([textquests.ai](https://www.textquests.ai/)) which harness, reply format and number of attempts produced each result, or re-run the paper's models with the maintained harness.
- Count an API error separately from a reply without an action: retry API errors with backoff, and do not end the game on them.
- Record in the result file when a game ended on failed attempts, and report those games separately.
- Tell the model when its reply had no action, so that a retry is not the same request.
