"""Per-sample results, written by the solver and read by the scorer."""

from inspect_ai.util import StoreModel
from pydantic import BaseModel, Field


class StepLog(BaseModel):
    """One turn, in the same shape as an entry of upstream's per-game results JSON."""

    step: int
    observation: str
    score: int
    progress: int
    game_over: bool
    reasoning: str
    action: str
    label_vectors: list[list[int]]


class TextQuestsStore(StoreModel):
    game: str = ""
    steps: int = 0
    progress: int = 0
    max_score: int = 0
    harm: int = 0
    restores: int = 0
    restarts: int = 0
    finished: bool = False
    # "finished", "max_steps", "parse_failure" or "" if the solver did not run to completion
    ended: str = ""
    log: list[StepLog] = Field(default_factory=list)
