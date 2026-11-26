# 09. Data: sherlock's manual text is missing, five games need package items that exist only as scans the agent is not given, and the dataset does not have a licence or a card and has moved

## Where

Hugging Face dataset [`longphann/textquests`](https://huggingface.co/datasets/longphann/textquests), revision `be34a3a` (`textquests_data.zip`). The same files are in [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at `18dc472`, `data/jiminy-cricket/` (`diff -r` reports them identical).

The environment loads only `feelies/feelies_text.txt` (always) and `feelies/invisiclues.txt` (with clues) into the system prompt ([simple-evals `textquests/src/textquests_env.py` lines 118–133](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/src/textquests_env.py#L118-L133)).

## What happens

- **sherlock** has no `feelies/feelies_text.txt` (its `feelies/` holds only `invisiclues.txt`), so its system prompt does not have a Guidelines section. It is the only game without one. sherlock also needs the tide times printed in the package newspaper, which the data does not contain in any form.
- **Package items as scans only.** Each game's `feelies/scans/` holds images of the original package. The agent is not shown them, and `feelies_text.txt` does not transcribe these items, which five games cannot be finished without:

  | Game            | Item                                                                  | File                                                |
  | :-------------- | :-------------------------------------------------------------------- | :-------------------------------------------------- |
  | ballyhoo        | the radio station's frequency, in the station's advertisement         | `ballyhoo/feelies/scans/traveling-circus10.jpeg`    |
  | cutthroats      | the wreck coordinates and depths on the map of shipwrecks             | `cutthroats/feelies/scans/wrecks-map.jpeg`          |
  | infidel         | the dig site, marked on the Professor's map                           | `infidel/feelies/scans/infidel-map.jpeg`            |
  | lurkinghorror   | the computer password, handwritten on the guide's directory page      | `lurkinghorror/feelies/scans/gue6.jpeg`             |
  | plunderedhearts | the pose shown on the fifty-guinea banknote, which opens the portrait | `plunderedhearts/feelies/scans/fifty-guineas1.jpeg` |

- **Licence and card.** The dataset repository holds two files, `.gitattributes` and `textquests_data.zip`. It does not have a dataset card (`README.md`), and the Hub API reports neither card data nor a licence. The zip contains Infocom's story files as recompiled by the Jiminy Cricket project, their source, manuals, hint booklets and package scans. Neither the dataset nor the GitHub repositories say who holds the rights to that material or on what terms it is redistributed. The repositories' MIT `LICENSE` files do not say whether they cover it.
- **Renamed.** `textquests_eval.py` downloads `https://huggingface.co/datasets/justinphan3110/textquests/resolve/main/textquests_data.zip` ([line 35](https://github.com/centerforaisafety/simple-evals/blob/8e53435/textquests/textquests_eval.py#L35)). That URL now redirects (HTTP 307) to `longphann/textquests`. The download is not pinned to a revision or checked against a hash.

## Reproduce

With the zip of revision `be34a3a` unpacked to `data/textquests/` (as `textquests_eval.py` unpacks it), from the directory that contains `data/`:

```bash
ls data/textquests/sherlock/feelies/
for g in data/textquests/*/; do [ -f "$g/feelies/feelies_text.txt" ] || basename "$g"; done
grep -c -i -e 1170 -e wpdl data/textquests/ballyhoo/feelies/feelies_text.txt
curl -s https://huggingface.co/api/datasets/longphann/textquests | jq -c '{sha, cardData, siblings: [.siblings[].rfilename]}'
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://huggingface.co/api/datasets/justinphan3110/textquests
```

Output (2026-11-26):

```text
invisiclues.txt
sherlock
0
{"sha":"be34a3a9821ba2dd4eb46096a55e9062f6b6d1db","cardData":null,"siblings":[".gitattributes","textquests_data.zip"]}
307 https://huggingface.co/api/datasets/longphann/textquests
```

The third command checks for ballyhoo's station in its manual text; the other four items can be checked the same way against each game's `feelies_text.txt`.

## Effect on results

- In the five games above, an agent that plays well still cannot reach the later checkpoints except by guessing (sweeping the radio dial, digging at random, trying poses), In the with-clues setting infidel's InvisiClues booklet gives the dig site's coordinates; the other four booklets do not give these items.
- sherlock is played without its manual, and seven of its twelve checkpoints are reached only after the moss is taken at high tide, whose times are in the missing newspaper; an agent can find the window by repeated attempts.
- Without a licence or card, users of the benchmark cannot tell whether they may redistribute the data, and a renamed or replaced repository changes what an unpinned download gets.

## Suggested fix

- Add sherlock's manual text, and transcribe the five items above (or give the agent the scans, as images, with its first turn).
- Add a dataset card that states the provenance of each part (Infocom, Jiminy Cricket, the benchmark's own files) and the terms under which it is distributed.
- Pin the download in `textquests_eval.py` to a revision and a SHA-256, and point it at the current repository name.
