# Upstream reports

Reports of faults in the upstream TextQuests benchmark ([arXiv 2507.23701](https://arxiv.org/abs/2507.23701)). Each report is written so that it can be filed as an upstream issue as it stands. They are kept in this repository and have not been filed. Anyone is free to file them upstream.

## What the reports are about

- The maintained harness: [centerforaisafety/simple-evals](https://github.com/centerforaisafety/simple-evals), directory `textquests/`, at commit `8e53435`. `tests/textquests/upstream/` in this repository holds its `textquests_env.py` and `game_info.py` and two functions of `textquests_eval.py` at that commit, unmodified apart from a header.
- The original harness, which produced the paper's results: [centerforaisafety/textquests](https://github.com/centerforaisafety/textquests) at commit `18dc472`.
- The data: the Hugging Face dataset [`longphann/textquests`](https://huggingface.co/datasets/longphann/textquests), formerly `justinphan3110/textquests`, at revision `be34a3a` (`textquests_data.zip`). Its files are the same as `data/jiminy-cricket/` in the original repository at `18dc472`.

The reproductions were run on Linux with Python 3.12 and Jericho 3.3.1.

## Why they are here

They are kept here because upstream shows little activity. As of 2026-11-26:

- centerforaisafety/textquests: the last commit is `18dc472`, a README change of 2025-12-02. Issue #2 has been open since 2025-08-01 and pull requests #4 and #5 since 2025-08-17, each without a comment or review; pull request #6 has been open since 2025-11-01, also without a comment or review. The last merged pull requests, #7 and #8, were opened on 2025-11-16 and merged on 2025-12-02.
- centerforaisafety/simple-evals: `textquests/` was added on 2025-11-14 and last changed on 2025-11-19 (`e2644c3`). The repository's latest commit, `8e53435` of 2026-07-14, changes other benchmarks. Its issue tracker is open and has not had an issue filed; its four pull requests were opened by one account and merged within two minutes of opening.
- `longphann/textquests`: two commits, both on 2025-11-13 (an initial commit and the upload of `textquests_data.zip`). The URL in `textquests_eval.py`, under `justinphan3110/textquests`, redirects to it.

## How a report is laid out

Each report has a title that states the fault, then:

- **Where**: repository, file and lines at the commits above, or the data file.
- **What happens**: the mechanism.
- **Reproduce**: a script or command to run against upstream's own code or data, and the output it printed. The scripts run from `textquests/` in a checkout of simple-evals, with the data unpacked at `textquests/data/textquests/`, where `textquests_eval.py` unpacks it. Scripts that make the game write files work in a new temporary directory.
- **Effect on results**: what the fault does to scores, with numbers where they were measured.
- **Suggested fix**.

Several reports give numbers from two runs with the tag format (GPT-4.1 and GPT-5, 25 games, up to 500 steps, made on 2026-11-22 with this repository's `textquests` task) and from the 25 bundled walkthroughs. This repository's environment gives the same observations, scores, progress, annotations and game-over state as upstream's at every turn of those sequences up to the first file command of report 01 (`tests/textquests/test_upstream_fidelity.py` checks the walkthroughs and the first 150 actions of every game in both runs). The numbers attributed to upstream come from replaying the sequences through upstream's environment.

## Reports

The last column says whether this repository's `textquests` task keeps upstream's behaviour or departs from it.

| Report                                       | Fault                                                                                                                                                                                            | `textquests`                                                                                                                                                   |
| :------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [01](01-file-commands.md)                    | `save`, bare `restore`, `script`, `#record` and `#command` read and write files in the working directory; a saved game is picked up by later runs; chained forms get past the blacklist          | Departs: refuses the file commands, also inside a chained action. Keeps the blacklist as upstream matches it, so `look. superbrief` and `quit.` reach the game |
| [02](02-crash-paths.md)                      | The `-visited` filter, markers without an annotation, `taken` markers without an object and a non-integer Moves field raise exceptions; the harness scores the game as if it had been played out | Departs: tolerates all four                                                                                                                                    |
| [03](03-scored-text-not-game-output.md)      | The System Warning line quoting a long action, annotation-marker fields and the status line are matched against checkpoints                                                                      | Keeps                                                                                                                                                          |
| [04](04-game-over-detection.md)              | Game over comes from Jericho's text match on "You have died"/"You have won": it fires on deaths the game recovers from and misses or delays most endings                                         | Keeps                                                                                                                                                          |
| [05](05-status-lines-and-compressed-text.md) | Status-line redraws stay in observations, the status-line pattern deletes game text, and trinity's yes/no prompt is split across turns                                                           | Keeps                                                                                                                                                          |
| [06](06-restart-substring.md)                | Any action containing "restart" restarts the game and resets the restore count                                                                                                                   | Keeps                                                                                                                                                          |
| [07](07-walkthroughs.md)                     | moonmist's and seastalker's walkthroughs skip the name prompt, trinity's is longer than 500 steps, and most only finish under seed 1                                                             | Keeps the data as shipped; `textquests_walkthrough` plays the two walkthroughs with the name prompt answered                                                   |
| [08](08-reply-format-and-retries.md)         | The maintained harness uses tags and 3 attempts, the paper's results JSON and 10; GPT-5 loses games to bare `analysis` replies under tags with the Responses API                                 | Keeps: `-T output_format` selects either harness's format and number of attempts. Inspect retries API errors, which upstream counts as failed attempts         |
| [09](09-data.md)                             | sherlock's manual text is missing; five games need package items that exist only as scans; the dataset does not have a licence or a card and has been renamed                                    | Keeps                                                                                                                                                          |
