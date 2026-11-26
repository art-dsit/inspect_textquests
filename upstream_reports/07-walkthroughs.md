# 07. moonmist's and seastalker's walkthroughs skip the name prompt, trinity's is longer than the step budget, and most only finish under seed 1

## Where

Hugging Face dataset [`longphann/textquests`](https://huggingface.co/datasets/longphann/textquests), revision `be34a3a`, `textquests_data.zip` (the same files are in [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472`, `data/jiminy-cricket/`):

- `moonmist/moonmist_walkthrough.txt`, `seastalker/seastalker_walkthrough.txt`, `trinity/trinity_walkthrough.txt`, and the other `<game>/<game>_walkthrough.txt`.
- `moonmist/initial_actions.txt`, `seastalker/initial_actions.txt`: the missing opening actions. Neither harness reads these files.

The walkthroughs are used by `TextQuestsEnv(starting_percentage=...)` ([simple-evals `textquests/src/textquests_env.py` lines 106–116](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L106-L116)), which asserts `seed == 1`.

## What happens

- **seastalker** opens with `Please type your first name.` and the walkthrough's first line, `turn screen on`, is taken as the name (`Hello Turn Screen On! Now type your last name.`). Every later action is then out of step with the game.
- **moonmist**'s walkthrough starts after the opening sequence (leaving the car, touching the gate's eye, the name and favourite-colour prompts). Its first action, `S`, is answered `Too bad, but the front gate is closed.`
- `initial_actions.txt` holds those opening actions (`Ro`, `Bot`, `yes` and `OUT`, `TOUCH EYE`, `Ro Bot`, `YES`, `GREEN`, `YES`). With them first, both walkthroughs finish.
- **trinity**'s walkthrough reaches 100% at its 576th action, past the 500-step budget.
- The walkthroughs give fixed answers to things the game draws at random (passwords, where characters go, the outcomes of fights and spells). The environment's default seed is 1 and `textquests_eval.py` does not pass another, so every run plays the world the walkthroughs were written for. Under seeds 2 and 3, 4 of the 25 walkthroughs finish.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`. It takes a few minutes.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv
from src.game_info import game_info

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())

def lines(path):
    return open(path).read().split("\n")

def replay(game, seed=1, prefix=()):
    """Best progress and the score when the walkthrough stops, as play_single_game stops."""
    env = TextQuestsEnv(f"{DATA}/{game}", seed=seed)
    best = 0
    for action in [*prefix, *lines(f"{DATA}/{game}/{game}_walkthrough.txt")]:
        obs, _, _, info = env.step(action)
        best = max(best, info.get("game_progress", 0))
        if best == 100 or info["score"] == game_info[game]["max_score"]:
            break
    return best, info["score"]

print("game             seed 1      seed 2      seed 3      (progress, score)")
for game in sorted(game_info):
    print(f"{game:16}", "".join(f"{str(replay(game, seed)):12}" for seed in (1, 2, 3)).rstrip())

print("With the data's initial_actions.txt played first, seed 1:")
for game in ["moonmist", "seastalker"]:
    prefix = [a for a in lines(f"{DATA}/{game}/initial_actions.txt") if a]
    print(f"{game:16}", replay(game, prefix=prefix), prefix)
```

Output (Jericho 3.3.1):

```text
game             seed 1      seed 2      seed 3      (progress, score)
ballyhoo         (100, 200)  (100, 200)  (100, 200)
borderzone       (98, 40)    (35, 8)     (35, 8)
cutthroats       (100, 180)  (50, 90)    (80, 140)
deadline         (100, 17)   (92, 10)    (92, 10)
enchanter        (100, 400)  (70, 235)   (70, 235)
hitchhiker       (100, 410)  (30, 60)    (30, 60)
hollywoodhijinx  (100, 150)  (93, 110)   (93, 110)
infidel          (100, 410)  (100, 410)  (100, 410)
lurkinghorror    (100, 100)  (30, 30)    (85, 75)
moonmist         (10, 1)     (10, 1)     (10, 1)
planetfall       (100, 85)   (70, 42)    (0, 0)
plunderedhearts  (100, 25)   (100, 25)   (100, 25)
seastalker       (0, 1)      (0, 1)      (0, 1)
sherlock         (100, 99)   (35, 44)    (35, 44)
sorcerer         (100, 400)  (7, 50)     (7, 50)
spellbreaker     (100, 600)  (0, 40)     (15, 80)
starcross        (100, 400)  (0, 0)      (0, 0)
stationfall      (100, 80)   (0, 0)      (0, 0)
suspect          (100, 21)   (75, 15)    (75, 12)
trinity          (100, 100)  (82, 80)    (95, 91)
wishbringer      (100, 100)  (68, 70)    (68, 70)
witness          (100, 14)   (100, 14)   (100, 14)
zork1            (100, 360)  (15, 20)    (15, 30)
zork2            (100, 410)  (5, 5)      (15, 10)
zork3            (100, 8)    (55, 6)     (55, 6)
With the data's initial_actions.txt played first, seed 1:
moonmist         (100, 23) ['OUT', 'TOUCH EYE', 'Ro Bot', 'YES', 'GREEN', 'YES']
seastalker       (100, 105) ['Ro', 'Bot', 'yes']
```

borderzone stops at 98 because it reaches the maximum score first. Under seed 1, trinity reaches 100 at action 576 of 605.

## Effect on results

- The walkthroughs are the only oracle shipped with the benchmark. As shipped, two of them cannot check the environment, and `starting_percentage` places moonmist and seastalker in a derailed game.
- A trinity episode that follows the published solution does not finish within 500 steps; a route of 465 actions reaches 100% under seed 1.
- Because the seed is fixed, the random elements of every game (borderzone's password, which is another word under seed 5; which of three messages trinity prints when the lump of metal is taken; the movements of characters) are the same in every run, and are those of the published walkthroughs.

## Suggested fix

- Prepend `initial_actions.txt` to the moonmist and seastalker walkthroughs (or merge the files).
- Ship a trinity walkthrough that finishes within 500 actions.
- Record in the data's README that the walkthroughs are for seed 1, or let the harness take a seed and report results over several.
