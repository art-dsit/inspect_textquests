# 06. Any action containing the substring "restart" restarts the game

## Where

[centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`, `textquests/src/textquests_env.py`, [lines 219–222](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L219-L222) (`elif 'restart' in action_str:`) and [lines 345–347](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L345-L347) (`reset()` sets `total_restores` and `game_progress` to 0).

[centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472` has the same code in `src/textquests_env.py`.

## What happens

`step` tests `'restart' in action_str` on the whole lower-cased action, so `ask floyd about restarting`, `read the leaflet to see how to restart the game` or `look. restart` restarts the game, without the confirmation the games ask for. The restart also sets `total_restores` to 0, so the `total_restore` the harness writes to the result file counts only the restores since the last restart. The checkpoints taken before the restart are kept, so `restore N` still returns to them.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())

env = TextQuestsEnv(f"{DATA}/zork1")
obs, info = env.reset()
actions = ["open mailbox", "take leaflet", "restore 1", "take leaflet",
           "read the leaflet to see how to restart the game", "inventory"]
for action in actions:
    env.save_checkpoint(obs, info)  # as play_single_game does
    obs, _, done, info = env.step(action)
    print(f"{action!r:50} -> {' '.join(obs.split())[:40]!r:44} restores={env.get_total_restores()}")
```

Output (Jericho 3.3.1):

```text
'open mailbox'                                     -> 'Opening the small mailbox reveals a leaf'   restores=0
'take leaflet'                                     -> 'Taken.'                                     restores=0
'restore 1'                                        -> 'Opening the small mailbox reveals a leaf'   restores=1
'take leaflet'                                     -> 'Taken.'                                     restores=1
'read the leaflet to see how to restart the game'  -> 'ZORK I: The Great Underground Empire Inf'   restores=0
'inventory'                                        -> 'You are empty-handed.'                      restores=0
```

## Effect on results

- An action that mentions restarting loses the game's state, and the restore count reported for the game drops.
- In two 500-step runs with the tag format (GPT-4.1 and GPT-5), every action containing "restart" was the command `restart` alone (85 times in GPT-4.1's run, 3 in GPT-5's), so this did not change those runs.

## Suggested fix

- Restart only when the whole action, stripped and lower-cased, is `restart`.
- Keep a count of restores over the whole episode, across restarts, for the result file.
