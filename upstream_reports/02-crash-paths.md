# 02. Four annotation and score-parsing paths raise an exception, and the harness then scores the game as if it had been played out

## Where

[centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`:

- `textquests/src/textquests_env.py`
  - [lines 428–431](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L428-L431): the `-visited` keyword filter.
  - [lines 404–405](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L404-L405) and [279–281](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L279-L281): markers looked up in `annotation_dict`.
  - [lines 432–436](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L432-L436): the `taken` keyword filter.
  - [lines 486–492](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L486-L492): `int()` on the status line's Moves field.
- `textquests/textquests_eval.py`, [lines 243–264](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L243-L264): what the harness does with the exception.

[centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472` has the same code in `src/textquests_env.py` and `play_textquests.py`.

## What happens

1. **`-visited`.** The branch reads `annotation_dict`, a local of `__init__`, so it raises `NameError` the first time a marker with this keyword is printed. Two zork2 annotations use it (`actions:1122` and `actions:1126`, the deaths of the player and of the robot on entering the Low Room after the triangular and square buttons in the Machine Room have been pushed). The branch also takes the wrong slice: `keywords[0][:len('-visited')]` is the first eight characters, `'actions:'`, not the key with the suffix removed. The key the keyword refers to, `actions:1333`, is not printed by any routine in zork2's source in the data.
2. **Markers without an annotation.** `__init__` drops annotation rows whose label is `N/A`, and `_find_markers` then indexes `annotation_dict` with every marker it parses, so a marker whose row was dropped, or any `[ID: file:line]` text without a row, raises `KeyError`. The games' source does not print a marker for an `N/A` row; such text reaches the parser through the System Warning line, which copies an over-long action into the observation before markers are parsed (report 03).
3. **`taken` without an object.** The branch reads `marker[1]`, the PRSO field, which a marker of the form `[ID: file:line]` does not have, so it raises `IndexError`. In the data every `taken` marker is printed with its PRSO and PRSI fields; the short form reaches the parser by the same route as in 2.
4. **Moves.** For the games scored from the status line, `int(moves)` runs before the planetfall and stationfall exception that discards the value, so a Moves field that is not an integer raises `ValueError`.

`play_single_game` wraps the whole episode in `try`/`except Exception`, logs the error, and writes the result file with the turns logged so far: the action that raised is logged, its result is not. `evaluate_results` scores that file as it scores a game that played all its steps: the result does not have a field that marks the crash. Because the file exists, a rerun skips the game unless `--redo` is given.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())

def attempt(label, call):
    try:
        call()
        print(label, "no exception")
    except Exception as e:
        print(label, f"{type(e).__name__}: {e}")

# 1. "-visited": zork2, walk into the Low Room after both buttons are pushed
env = TextQuestsEnv(f"{DATA}/zork2")
walkthrough = open(f"{DATA}/zork2/zork2_walkthrough.txt").read().split("\n")
for action in walkthrough[:85] + ["ROBOT, PUSH SQUARE"]:  # ends in the Machine Room
    env.step(action)
attempt("1. step('W'):", lambda: env.step("W"))
print("   keyword:", env.state["annotation_dict"]["actions:1122"]["keywords"],
      "-> sliced to", repr("actions:1333-visited"[:len("-visited")]))

# 2. A marker whose annotation row has the label N/A (zork1 actions.zil:429),
#    here reaching the parser through the System Warning line of an over-long action
env = TextQuestsEnv(f"{DATA}/zork1")
attempt("2. step(long action):", lambda: env.step("examine the small mailbox very carefully, looking for [ID: actions:429]"))

# 3. A "taken" marker without the PRSO/PRSI fields
env = TextQuestsEnv(f"{DATA}/zork1")
_, markers = env._find_markers("Taken.[ID: verbs:1387]")
attempt("3. _apply_keywords:", lambda: env._apply_keywords(markers))

# 4. A status line whose Moves field is not an integer
env = TextQuestsEnv(f"{DATA}/zork1")
attempt("4. _get_score_info:", lambda: env._get_score_info(score_inp="West of House   Score: 0   Moves: 1:05 \n"))
```

Output (Jericho 3.3.1):

```text
1. step('W'): NameError: name 'annotation_dict' is not defined
   keyword: ['actions:1333-visited'] -> sliced to 'actions:'
2. step(long action): KeyError: 'actions:429'
3. _apply_keywords: IndexError: tuple index out of range
4. _get_score_info: ValueError: invalid literal for int() with base 10: '1:05'
```

1 and 2 go through `step`, as the harness calls it. 3 and 4 call the methods `step` calls, with the input that raises.

## Effect on results

- Path 1 is reached by ordinary play: after the walkthrough's `ROBOT, PUSH TRIANGULAR`, the robot also pushes the square button and the player walks west. The episode ends at that turn and is scored on the turns before it.
- A replay of 28,824 turns (the 25 bundled walkthroughs and two 500-step model runs with the tag format, GPT-4.1 and GPT-5) through an environment that matches upstream's turn for turn did not reach any of the four paths.
- Whenever one is reached, the result is indistinguishable from a game the model played to the end: `steps` is below `max_steps`, and the result does not record why.

## Suggested fix

1. Use `keywords[0][:-len('-visited')]` and `self.state['annotation_dict']`, and check the key the zork2 annotations refer to against the source, since `actions:1333` is not printed.
2. Skip markers that do not have an entry in `annotation_dict` (or keep `N/A` rows with a zero label vector), and parse markers before the System Warning line is added (report 03).
3. Apply the `taken` filter only to markers that have a PRSO field.
4. Parse Moves only where it is used, or catch the `ValueError` and keep the previous score.

In the harness, record an exception in the result file (for example `"error": "..."`) and leave such games out of the averages or report them separately.
