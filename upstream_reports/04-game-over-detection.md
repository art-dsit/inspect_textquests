# 04. The harness's game over is Jericho's `done`, which for these story files is a text match on "You have died" and "You have won"

## Where

- [centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`:
  - `textquests/src/textquests_env.py`, [line 242](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L242) (the returned `game_over` is Frotz's `done`) and [lines 249 and 257](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L249-L257) (the environment's own `state['game_over']`, from the `[EVENT: GAME OVER]` marker, which makes later actions return `Impossible.` at [lines 225–228](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L225-L228)).
  - `textquests/textquests_eval.py`, [lines 176–185](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L176-L185) and [241](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L241): the restore-or-restart prompt is added to the next observation when `done` is true.
- [microsoft/jericho](https://github.com/microsoft/jericho) `frotz/src/games/default.c`: `default_game_over()` and `default_victory()` return true when the screen text contains `****  You have died  ****` or `****  You have won  ****`. The recompiled story files in the data are not in Jericho's list of supported games (`FrotzEnv.is_fully_supported` is `False` for all 25; the environment hides the warning), so these defaults are what `done` reports.
- [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472`: the same code in `src/textquests_env.py` and `play_textquests.py`.

## What happens

The environment has two game-over signals that disagree. The harness uses `done`, the text match. The environment's own flag comes from the `[EVENT: GAME OVER]` marker that the Jiminy Cricket recompilation prints at most endings. As a result:

- **A death the game recovers from is reported as game over.** zork1–3, enchanter, spellbreaker and starcross print `****  You have died  ****` and revive the player. `done` is true, the harness tells the model to restore or restart, and the game is still playable.
- **Endings without the banner are reported one turn late.** At an ending that prints the marker but not the death or win banner (the win in zork1, and the endings counted under "Endings with the marker" in the table below), `done` is false on that turn and the harness does not add the prompt. The next action gets `Impossible.` and `done` true.
- **Some endings are not detected at all.** Endings that call `QUIT` without the marker leave both signals false and the game running: deadline's deaths and its 8 pm time limit print their text and play continues; borderzone's failed chapters print the game's restart prompt again on every turn.
- **An interpreter halt is not an ending to the environment.** Where a game ends with `QUIT` as the last instruction of a routine (hitchhiker's time-travel paradox in the pub, `I-UNEASY` in `earth.zil`; witness's 8:00 a.m. time limit, `TIMES-UP` in `events.zil`), the interpreter halts with a runtime error; in hitchhiker the ending text does not reach the observation. Every later action returns `Emulator halted due to runtime error.` with `done` true while `state['game_over']` stays false, and `restore N` returns the checkpoint's observation but does not restart the interpreter.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())

def play(game, setup, actions):
    """Play `setup` (a list, or that many walkthrough actions), then `actions`, as play_single_game does."""
    env = TextQuestsEnv(f"{DATA}/{game}")
    obs, info = env.reset()
    if isinstance(setup, int):
        setup = open(f"{DATA}/{game}/{game}_walkthrough.txt").read().split("\n")[:setup]
    for i, action in enumerate(setup + actions):
        env.save_checkpoint(obs, info)
        obs, _, done, info = env.step(action)
        if i >= len(setup):
            text = " ".join(obs.split())
            print(f"  {game} {action!r}: done={done} game_over={env.state['game_over']} {text[:45]!r}...{text[-30:]!r}")

print("1. A death the game recovers from")
play("zork1", ["n", "e", "open window", "w", "w", "move rug", "open trap door", "d"], ["n", "look"])
print("2. A win that carries the game-over marker")
play("zork1", 347, ["enter barrow", "look"])
print("3. Endings that are not detected")
play("deadline", 79, ["jump", "look"])
play("borderzone", 50, ["wait", "look"])
print("4. An interpreter halt")
play("hitchhiker", 236, ["S", "W", "wait", "wait", "wait", "wait", "restore 237", "look"])
```

Output (Jericho 3.3.1); `game_over` is the environment's `state['game_over']`:

```text
1. A death the game recovers from
  zork1 'n': done=True game_over=False 'Oh, no! A lurking grue slithered into the roo'...' there appears to be sunlight.'
  zork1 'look': done=False game_over=False 'Forest This is a forest, with trees in all di'...' there appears to be sunlight.'
2. A win that carries the game-over marker
  zork1 'enter barrow': done=False game_over=True 'Inside the Barrow As you enter the barrow, th'...'pe RESTART, RESTORE, or QUIT):'
  zork1 'look': done=True game_over=True 'Impossible.'...'Impossible.'
3. Endings that are not detected
  deadline 'jump': done=False game_over=False 'For a brief moment, you feel the exhilaration'...'ast thought. Wheeeeeeeeee!!!!!'
  deadline 'look': done=False game_over=False 'Library Balcony The balcony is bare of furnit'...'lcony and the library is open.'
  borderzone 'wait': done=False game_over=False 'Time passes... Your contact looks around nerv'...'START, RESTORE, HINT, or QUIT)'
  borderzone 'look': done=False game_over=False '> Would you like to start over, restore a sav'...'START, RESTORE, HINT, or QUIT)'
4. An interpreter halt
  hitchhiker 'S': done=False game_over=False 'Country Lane'...'Country Lane'
  hitchhiker 'W': done=False game_over=False 'Pub There is a barman serving at the bar. You'...'u feel uneasy about something.'
  hitchhiker 'wait': done=False game_over=False 'Time passes... You still feel uneasy.'...'sses... You still feel uneasy.'
  hitchhiker 'wait': done=False game_over=False 'Time passes... You still feel uneasy.'...'sses... You still feel uneasy.'
  hitchhiker 'wait': done=False game_over=False 'Time passes... You still feel uneasy.'...'sses... You still feel uneasy.'
  hitchhiker 'wait': done=True game_over=False 'Emulator halted due to runtime error.'...'r halted due to runtime error.'
  hitchhiker 'restore 237': done=False game_over=False 'Country Lane'...'Country Lane'
  hitchhiker 'look': done=True game_over=False 'Emulator halted due to runtime error.'...'r halted due to runtime error.'
```

In 1 the player is killed by the grue and wakes in the forest; the harness's next prompt tells the model to restore or restart. In 3 the deadline player falls to his death and is standing on the balcony on the next turn.

## Effect on results

Replaying the logged actions of two 500-step runs with the tag format through upstream's environment, as `play_single_game` drives it, up to the first `save`, bare `restore` or `hint` in each game:

| Run     | Turns  | `done` true, `state['game_over']` false                              | Endings with the marker and `done` false                                                                      | Interpreter halts                                                                                                                              |
| :------ | -----: | :------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| GPT-4.1 | 11,314 | 18 (spellbreaker 9, starcross 4, enchanter 2, zork1, zork2, zork3)   | 20 (trinity 5, suspect 4, witness 3, deadline, plunderedhearts and wishbringer 2 each, ballyhoo, hitchhiker)  | moonmist, from action 50: every later action returns `Emulator halted`, including the first action after each of the model's three `restore N` |
| GPT-5   | 10,356 | 17 (zork2 8, enchanter 3, spellbreaker 3, starcross 2, hitchhiker 1) | 24 (wishbringer 7, plunderedhearts 6, seastalker 4, sherlock and suspect 2 each, ballyhoo, sorcerer, trinity) | 0                                                                                                                                              |

Each of the first kind sends the model a restore-or-restart prompt while the environment still accepts actions; in zork1–3, enchanter, spellbreaker and starcross these are deaths the game recovers from. Each of the second costs the model a turn on `Impossible.` before the prompt arrives.

## Suggested fix

- Use the environment's `state['game_over']` (the `[EVENT: GAME OVER]` marker) as the harness's game over, and add the restore-or-restart prompt on the turn the marker is printed.
- Treat an interpreter halt (`env._emulator_halted()`, or the `Emulator halted` text) as a game over, and reset the interpreter on `restore N` after one.
- Add markers, or per-game ending texts, for the endings the recompilation leaves unmarked: deadline's `QUIT` calls (`clock.zil` `CLOCKER`, `verbs.zil` `V-LEAP`, `actions.zil` `MASTER-BEDROOM-F`, `BEDROOM-BALCONY-F`, `GLOBAL-ENDING-F`), witness's `TIMES-UP` and `FIRE-SHOT`, zork3's `JIGS-UP` after the last death, and borderzone's chapter-1 and chapter-3 failures.
