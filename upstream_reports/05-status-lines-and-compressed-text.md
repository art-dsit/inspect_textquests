# 05. Status-line redraws stay in observations, the status-line pattern deletes game text, and trinity's compressed text is split across turns

## Where

[centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals) at `8e53435`, `textquests/src/textquests_env.py`:

- [lines 373–388](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L373-L388), `_remove_status_line`: `'.+Score: .+Moves: .+\n'` for the games with a score status line, `'>.*Time:.*\n'` for the games with a clock, and only a leading `'>\n'` for trinity, borderzone and sherlock.
- [lines 139–149](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L139-L149) and [186–188](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L186-L188), `_replace_text`: `[RIDX: n]` markers of the compressed games are expanded one observation at a time.

[centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472` has the same code in `src/textquests_env.py`.

## What happens

- **Redraws stay.** When one action spans several game turns (`wait`, `wait until`, a long search), the interpreter redraws the status line once per turn. In the clock games (cutthroats, wishbringer, witness, suspect, deadline, moonmist) only the first redraw follows the `>` prompt, so only the first matches `'>.*Time:.*\n'`; the rest stay in the observation, one per game minute. In the score games a redraw that is not followed by a newline also stays (seastalker, `SCIMITAR   Score: 85   Moves: 185   "Holy halibut!" cries Tip. ...`).
- **Game text is deleted.** In the score games the redraws can run together with event text on one line (`SCIMITAR   Score: 24   Moves: 59   The depth finder warning light changes to orange, ...`). `'.+Score: .+Moves: .+\n'` is greedy and deletes the line to its end, event text included.
- **borderzone, trinity, sherlock.** Only a leading `'>\n'` is removed, so borderzone's status display (the clock, `17:28`, and the room name padded with spaces) is in every observation.
- **trinity's split prompt.** trinity prints `[RIDX: 64]` for its yes/no prompt (`[Please type YES or NO.] >`). The marker arrives split across the input request: one observation ends in `[RIDX:` and the next begins with a space and `64]`, and `_replace_text` expands neither part.

## Reproduce

In a checkout of simple-evals at `8e53435`, with `jericho` and `numpy` installed and the data unpacked at `textquests/data/textquests/` (where `textquests_eval.py` unpacks it), save this as `textquests/repro.py` and run `python repro.py` from `textquests/`.

```python
import os, sys, tempfile
sys.path.insert(0, ".")  # run from simple-evals/textquests
from src.textquests_env import TextQuestsEnv

DATA = os.path.abspath("data/textquests")
os.chdir(tempfile.mkdtemp())

def walkthrough(game):
    return open(f"{DATA}/{game}/{game}_walkthrough.txt").read().split("\n")

# 1. deadline: the status line redrawn during a wait stays in the observation
env = TextQuestsEnv(f"{DATA}/deadline")
obs, *_ = env.step("wait")
print("1.", repr(obs))

# 2. seastalker: game text printed after a status-line redraw on the same line is deleted
env = TextQuestsEnv(f"{DATA}/seastalker")
for action in ["Ro", "Bot", "yes"] + walkthrough("seastalker")[:44]:  # answer the name prompt first
    env.step(action)
raw = []
frotz_step = env.env.step
env.env.step = lambda action: raw.append(frotz_step(action)) or raw[-1]
obs, *_ = env.step("wait")
sentence = "The depth finder warning light changes to orange"
print("2. interpreter output:", sentence in raw[0][0], " observation:", sentence in obs)

# 3. trinity: the compressed text of a yes/no prompt is split across two observations
env = TextQuestsEnv(f"{DATA}/trinity")
for action in walkthrough("trinity")[:255]:
    env.step(action)
obs, *_ = env.step("s")
print("3.", repr(obs[-40:]))
obs, *_ = env.step("no")
print("  ", repr(obs[:40]))
```

Output (Jericho 3.3.1):

```text
1. 'Time passes...\n South Lawn                                                                                                            Time:  8:01 am                    \n South Lawn                                                                                                            Time:  8:02 am                    \n South Lawn                                                                                                            Time:  8:03 am                    \n\nIt is now 8:03 am.\n\n'
2. interpreter output: True  observation: False
3. 'ou sure you want to go that way?\n\n[RIDX:'
   ' 64]\n\n"Smart move," sniggers a voice in '
```

In 2 the sentence is in the interpreter's output for the action and not in the observation the model is shown.

## Effect on results

- Status-line redraws do not match a checkpoint, but they fill the model's context: each `wait` or `wait until` in the clock games adds one line per game minute.
- Deleted text is game information the model does not get. Replaying seastalker's walkthrough (with the name prompt answered), text is deleted on 6 turns: the room description on reaching the sub's gangplank ("You're at a temporary runway or gangplank ..."), the depth-finder warnings, the message on passing the opening in the sea wall, and Doc Horvak taking out the dart gun.
- trinity's model is shown `[RIDX:` where the game asks for YES or NO.

## Suggested fix

- Remove every status-line redraw, not only the first: match the status line's fixed layout (room name, padding, `Time:` or `Score:`/`Moves:` fields) up to the end of the field, without requiring a leading `>` or a trailing newline, and keep the text after it.
- Remove borderzone's status display by the same method.
- Expand `[RIDX: n]` markers on the text accumulated across an input request, or hold back a trailing `[RIDX:` until the rest arrives.
