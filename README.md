# inspect_textquests

An [Inspect AI](https://inspect.aisi.org.uk/) implementation of
[TextQuests](https://arxiv.org/abs/2507.23701): LLM agents playing 25 classic Infocom text
adventures for up to 500 turns each, scored on progress through the game, in-game points and
moral harm.

The evaluation lives in [`src/textquests/`](src/textquests/README.md), which documents
usage, parameters, scoring, and the differences from the upstream harness.

```bash
uv sync
uv run inspect eval textquests/textquests --model openai/gpt-5-mini
```

Installing needs a C toolchain (Linux or macOS): the Jericho interpreter compiles Frotz.

## Development

```bash
uv sync --group dev
uv run pytest                      # fast tests; add RUN_SLOW_TESTS=1 for the 25 walkthrough replays
make check                         # ruff, mypy, inspect-evals-lint and the other repo checks
```

Tests marked `dataset_download` fetch the 191 MB game data on first run (set
`RUN_DATASET_DOWNLOAD_TESTS=0` to skip them).

This repository was created from the
[inspect-evals-template](https://github.com/Generality-Labs/inspect-evals-template) and keeps
its tooling: [CONTRIBUTING.md](CONTRIBUTING.md), [BEST_PRACTICES.md](BEST_PRACTICES.md),
[MANAGED_FILES.md](MANAGED_FILES.md) (which files the template sync may update), and
[`tools/enforcement.config`](tools/enforcement.config), which decides which of the checks run
by `make check` and CI block a merge and which are advisory.
