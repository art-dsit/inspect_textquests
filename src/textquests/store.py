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
    steps: int = 0
    progress: int = 0
    max_score: int = 0
    harm: int = 0
    # Percentages of every checkpoint reached, and how many of the Verified set that is
    checkpoints: list[int] = Field(default_factory=list)
    verified_reached: int = 0
    verified_total: int = 0
    restores: int = 0
    restarts: int = 0
    # "finished", "max_steps", "parse_failure", "context_limit", "walkthrough_exhausted",
    # or "" if interrupted
    ended: str = ""
    log: list[StepLog] = Field(default_factory=list)
