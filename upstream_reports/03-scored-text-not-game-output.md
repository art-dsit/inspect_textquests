# 03. Progress is credited from text that is not the game's output: the System Warning line, annotation markers and the status line

## Where

[centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`:

- `textquests/src/textquests_env.py`
  - [lines 235–246](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L235-L246): an action over 64 characters is cut to 64 and a `System Warning` line quoting the whole action is put in front of the observation.
  - [lines 249–256](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L249-L256): the live progress check, `info['game_progress']`, run before the status line and the annotation markers are removed at [lines 272–273](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L272-L273).
- `textquests/textquests_eval.py`
  - [lines 125–127](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L125-L127) and [235–237](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L235-L237): the live value ends the game at 100, and is written as `progress` in the result file ([line 253](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L253)).
  - [lines 282–290](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L282-L290) and [346–349](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L346-L349): the offline value, `get_game_progress` over the logged observations, which `evaluate_results` reports.

[centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472` has the same code in `src/textquests_env.py`, `play_textquests.py` and `eval_results.py`.

## What happens

Upstream computes progress twice. The live value is matched, during play, against the observation after the reward markers are removed and before the status line and the annotation markers are. The offline value is matched, after play, against the cleaned observations the model was shown. Three kinds of text that the game did not print as its response take part:

- **The System Warning line.** For an action over 64 characters the observation starts with `System Warning: Invalid length action command: <the whole action>`. The line stays in the cleaned observation, so it is matched by both the live and the offline computation: a long action that contains a checkpoint's text scores that checkpoint. The line also defeats the `observation[:2] == '>\n'` test that removes the prompt line in trinity, borderzone and sherlock, and it is parsed for annotation markers (report 02).
- **Annotation markers** (live value only). A marker has the form `[ID: file:line, PRSO: <object>, PRSI: <object>]`. Its object fields can contain a checkpoint's text, and a marker printed inside a checkpoint's text splits it so that it does not match.
- **The status line** (live value only). In the games whose status line shows the room, the room name matches room-name checkpoints on later turns in that room.

The live value decides when the game ends (at 100) and is the `progress` in each game's result file. The offline value is the number `evaluate_results` prints and averages. The two can differ for the same game.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`.

```python
import ast, json, os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

# get_game_progress, the offline computation, taken from textquests_eval.py
# (importing that module downloads the data and needs the shared/ package)
source = open("textquests_eval.py").read()
node = next(n for n in ast.parse(source).body if getattr(n, "name", "") == "get_game_progress")
exec(ast.get_source_segment(source, node))

DATA = os.path.abspath("data/textquests")
CHECKPOINTS = json.load(open(f"{DATA}/game_progress.json"))
os.chdir(tempfile.mkdtemp())

def walk(game, n):
    env = TextQuestsEnv(f"{DATA}/{game}")
    actions = open(f"{DATA}/{game}/{game}_walkthrough.txt").read().split("\n")
    for action in actions[:n]:
        obs, _, _, info = env.step(action)
    return actions[n - 1], obs, info

def show(label, game, action, obs, info):
    offline = get_game_progress(game, [obs], CHECKPOINTS)
    print(f"{label} {action!r} -> {' '.join(obs.split())[:70]!r}")
    print(f"   live {info['game_progress']}, offline {offline}")

# 1. An action over 64 characters is quoted back in a "System Warning" line
env = TextQuestsEnv(f"{DATA}/zork1")
action = "say You have mastered the first part of the ZORK trilogy, at last"
obs, _, _, info = env.step(action)
show("1.", "zork1", action, obs, info)

# 2. A marker's PRSO field supplies checkpoint text (lurkinghorror 70%: "bolt cutter")
show("2.", "lurkinghorror", *walk("lurkinghorror", 230))

# 3. A marker inside checkpoint text hides it (suspect 35%: "You are now carrying the business card")
show("3.", "suspect", *walk("suspect", 60))
```

Output (Jericho 3.3.1):

```text
1. 'say You have mastered the first part of the ZORK trilogy, at last' -> 'System Warning: Invalid length action command: say You have mastered t'
   live 100, offline 100
2. 'GET CUTTER' -> 'Taken.'
   live 70, offline 0
3. 'take business card' -> 'You are now carrying the business card.'
   live 15, offline 35
```

In 1 the model's first action scores zork1's 100% checkpoint, and `play_single_game` ends the game as finished on the next turn. In 2 the interpreter's text is `Taken.\n[ID: verbs:1422, PRSO: bolt cutter, PRSI: ]`. In 3 it is `You are now carrying [ID: verbs:1988, PRSO: business card, PRSI: ]the business card.`

## Effect on results

- In the runs of GPT-4.1 and GPT-5 with the tag format (25 games, 500 steps each, replayed through upstream's environment), the result files and `evaluate_results` disagree on three games: lurkinghorror with GPT-4.1 (live 70, offline 0: the 70% "bolt cutter" came from the PRSO field of `[ID: cs:6330, PRSO: bolt cutter, PRSI: ]`, printed when the maintenance man strangles the player) and suspect with both models (live 15, offline 35).
- On the bundled walkthroughs, the live value credits ballyhoo's 10% ("Camp, East", from `[ID: outside:2174, PRSO: Camp, East, PRSI: ]`) and lurkinghorror's 70% from marker fields, does not credit suspect's 35% and 60% or borderzone's 100% because a marker sits inside the text, and matches lurkinghorror's 15%, 20% and 25% room names in the status line on later turns in those rooms (which does not change the maximum there, as the room name was printed on arrival). borderzone's live value does not reach 100, so `play_single_game` does not end that game at the win; it ends when the score reaches the maximum.
- The two runs contain 18 actions over 64 characters. They do not contain checkpoint text, so the System Warning line did not change a result there; it would score any checkpoint whose text a model writes into a long action.

## Suggested fix

- Truncate the action and report it to the model separately from the observation (or put the warning after the checkpoint match and outside the logged observation), so that checkpoints and markers are not matched against the model's own words.
- Compute live progress on the cleaned observation, after `_remove_status_line` and `_find_markers`, so that the live and offline values agree and the game ends when the offline value reaches 100.
