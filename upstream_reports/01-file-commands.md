# 01. `save`, bare `restore`, `script` and the `#` debugging verbs read and write files in the working directory

## Where

- [centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`:
  - `textquests/src/game_info.py`, [lines 143–147](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/game_info.py#L143-L147): the blacklist that every game gets.
  - `textquests/src/textquests_env.py`, [lines 175–184](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L175-L184): the blacklist is matched against the whole action; anything that does not match goes to Frotz.
- [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472`: the same code in `src/game_info.py` and `src/textquests_env.py`.

## What happens

Every action that does not match the blacklist is passed to the Frotz interpreter. The blacklist does not contain `save` or `restore`, and each of its entries is anchored at the start of the action (`^script.*`, `^super.*`, `^quit$`), so it does not match a later command of a chained action such as `look. script`. Frotz's `save` writes `<game>.qzl` to the process's working directory without asking for a file name, and a bare `restore` reads it back. `textquests_eval.py` plays all games in one process with one working directory and does not remove the file, so a `restore` in any later run of the same game from that directory loads the position saved in an earlier run. Within a run, a bare `restore` is a rewind that `get_total_restores()` does not count. The games' own synonyms do the same: `suspend` in witness writes `witness.qzl`, `rescue` in stationfall writes `stationfall.qzl`. `script` writes a transcript to a file named after the input line. `#record` and `#command`, debugging verbs left in many of the games, write every input line to a file named `#record` (including the `look` the environment sends to read the score) and play commands from a file named `#command`, whose results then arrive one turn late.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`. The script works in a new temporary directory.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())  # Frotz reads and writes files in the working directory

def run(game, actions):
    env = TextQuestsEnv(f"{DATA}/{game}")
    for action in actions:
        obs, *_ = env.step(action)
        print(f"  {action!r:18} -> {' '.join(obs.split())[:50]!r}")

print("1. Save in one run, restore in the next")
run("zork1", ["open mailbox", "take leaflet", "save"])
run("zork1", ["restore", "inventory"])
print("2. Chained commands and debugging verbs")
run("zork1", ["script", "look. script", "#record", "north", "#unrecord", "look. superbrief", "quit."])
print("3. Per-game synonyms of save")
run("witness", ["suspend"])
run("stationfall", ["rescue"])
print("4. #command plays commands from a file")
open("#command", "w").write("n\nopen mailbox\n")
run("zork1", ["#command", "look"])
print("files:", sorted(os.listdir()))
print("#record holds:", repr(open("#record").read()))
```

Output (Jericho 3.3.1):

```text
1. Save in one run, restore in the next
  'open mailbox'     -> 'Opening the small mailbox reveals a leaflet.'
  'take leaflet'     -> 'Taken.'
  'save'             -> 'Ok.'
  'restore'          -> 'Ok.'
  'inventory'        -> 'You are carrying: A leaflet'
2. Chained commands and debugging verbs
  'script'           -> 'Impossible.'
  'look. script'     -> 'West of House You are standing in an open field we'
  '#record'          -> ''
  'north'            -> 'North of House You are facing the north side of a '
  '#unrecord'        -> ''
  'look. superbrief' -> 'North of House You are facing the north side of a '
  'quit.'            -> 'Your score is 0 (total of 360 points), in 5 moves.'
3. Per-game synonyms of save
  'suspend'          -> 'O.K. What should you, the detective, do now?'
  'rescue'           -> 'Okay.'
4. #command plays commands from a file
  '#command'         -> 'Do you want MORE prompts? (y/n) >n'
  'look'             -> 'Opening the small mailbox reveals a leaflet.'
files: ['#command', '#record', 'look. script', 'stationfall.qzl', 'witness.qzl', 'zork1.qzl']
#record holds: 'look\nnorth\nlook\n#unrecord\n'
```

The second `run("zork1", ...)` is a new environment: its `restore` loads the leaflet from the first. `script` alone is refused, `look. script` writes the transcript `look. script`, and `look. superbrief` and `quit.` reach the game.

## Effect on results

- Models type these commands. In a run of GPT-4.1 with the tag format (25 games, 500 steps, through an environment that matches upstream's turn for turn), the model typed `save` in zork3 (action 429) and seastalker (action 82), and a bare `restore` in plunderedhearts (action 288) and borderzone (action 278). Under upstream's environment the two restores fail (`Failed.`), as those games had not been saved; a later run of zork3 or seastalker from the same directory would find the saved file.
- `zork1.qzl` and `seastalker.qzl` were committed to the root of centerforaisafety/textquests in `32bf9e3` ("Example to GPT-5-mini", 2025-08-13) and deleted on 2025-09-02 (`dd4db30`, `9a749ba`).
- A saved game left in the working directory makes runs depend on what ran before them in that directory, and a bare `restore` within a run is a rewind that the reported `total_restore` does not include.

## Suggested fix

- Refuse `save`, `restore` without a step number, `script`, `unscript`, any command starting with `#`, and the per-game synonyms of save and restore (moonmist and seastalker `resume`; stationfall `rescue`; witness `suspend`, `pause`, `continue`, `resume`), as the environment refuses the blacklist.
- Match the blacklist against each command of a chained action (split on `.` and `then`), so that `look. superbrief` and `quit.` are refused as `superbrief` and `quit` are.
- Run each game in its own temporary working directory, so that a command the blacklist misses cannot affect another run.
