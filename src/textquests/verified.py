"""The checkpoints TextQuests Verified scores.

Epoch AI's review of the benchmark (https://epoch.ai/benchmarks/textquests/review, reviewed
2026-08-10, read 2026-11-23) replayed every walkthrough and flagged checkpoints that are
impossible to reach in a run, that fire for a wrong action, or that fail to fire for a right
one. EXCLUDED lists those, by game and checkpoint percentage. We did not repeat the audit.

Checkpoints Epoch flagged only as "inert" stay in: they are sound, and merely fire after a
higher-percentage one, which matters to the highest-checkpoint metric but not to a count.
"""

EXCLUDED: dict[str, frozenset[int]] = {
    "ballyhoo": frozenset({20}),
    "borderzone": frozenset({35, 85}),
    "cutthroats": frozenset({30, 80, 90, 100}),
    "deadline": frozenset({78, 92}),
    "enchanter": frozenset({60, 95}),
    "hitchhiker": frozenset({80}),
    "hollywoodhijinx": frozenset({22}),
    "infidel": frozenset({20}),
    "lurkinghorror": frozenset({5, 60, 70, 75, 100}),
    "moonmist": frozenset({35, 45, 90}),
    "plunderedhearts": frozenset({40}),
    "seastalker": frozenset({15, 50}),
    "sherlock": frozenset({55, 65, 70, 80, 90, 96, 100}),
    "spellbreaker": frozenset({45, 95}),
    "starcross": frozenset({60, 75}),
    "suspect": frozenset({35, 60, 85}),
    "trinity": frozenset({42, 71, 82, 92, 95, 100}),
    "zork1": frozenset({30}),
    "zork2": frozenset({5, 30, 40}),
    "zork3": frozenset({55}),
}


def verified_checkpoints(game: str, percentages: set[int]) -> set[int]:
    """The game's checkpoints that count: not excluded, and not the 0% "game started" one."""
    return {
        p for p in percentages if p > 0 and p not in EXCLUDED.get(game, frozenset())
    }
