"""Per-game constants from the upstream harness.

Max scores and the regexes for actions that can wedge the interpreter are copied from
https://github.com/centerforaisafety/textquests/blob/main/src/game_info.py (MIT), which in
turn derives from Hendrycks et al.'s Jiminy Cricket. Fields the harness never reads
(player_object, tell_objects, finished_keywords, ...) are not carried over.
"""

from dataclasses import dataclass, field

# Actions that can send a game into an infinite loop or otherwise break the interpreter.
# Matched case-insensitively against the lowercased action; a hit returns "Impossible.".
COMMON_BAD_ACTIONS = [
    "^brief.*",
    "^super.*",
    "^script.*",
    "^unscript.*",
    "otr0",
    "oflg0",
    "oflg1",
    "^q$",
    "^quit$",
]


@dataclass(frozen=True)
class GameInfo:
    max_score: int
    bad_actions: list[str] = field(default_factory=lambda: list(COMMON_BAD_ACTIONS))


GAME_INFO: dict[str, GameInfo] = {
    "ballyhoo": GameInfo(max_score=205),
    "borderzone": GameInfo(max_score=40),
    "cutthroats": GameInfo(max_score=250),
    "deadline": GameInfo(max_score=17),
    "enchanter": GameInfo(max_score=400),
    "hitchhiker": GameInfo(max_score=410),
    "hollywoodhijinx": GameInfo(max_score=150),
    "infidel": GameInfo(max_score=410),
    "lurkinghorror": GameInfo(max_score=105),
    "moonmist": GameInfo(max_score=23),
    "planetfall": GameInfo(max_score=85),
    "plunderedhearts": GameInfo(max_score=25),
    "seastalker": GameInfo(
        max_score=105,
        bad_actions=[
            "^(?:walk|go|run|proceed|steed|head|drive) (?!north|south|east|west|down|up|in|out)",
            "^suspend.*",
            "^pause.*",
            *COMMON_BAD_ACTIONS,
        ],
    ),
    "sherlock": GameInfo(max_score=100),
    "sorcerer": GameInfo(max_score=400),
    "spellbreaker": GameInfo(
        max_score=600,
        bad_actions=[
            "^turn off zipper",
            "^turn on zipper",
            "^break .*? with zipper",
            "^ride .*?zipper",
            *COMMON_BAD_ACTIONS,
        ],
    ),
    "starcross": GameInfo(max_score=400),
    "stationfall": GameInfo(max_score=80),
    "suspect": GameInfo(max_score=21),
    "trinity": GameInfo(max_score=105),
    "wishbringer": GameInfo(max_score=101),
    "witness": GameInfo(max_score=14),
    "zork1": GameInfo(max_score=360),
    "zork2": GameInfo(max_score=410),
    "zork3": GameInfo(max_score=8),
}

GAMES: list[str] = sorted(GAME_INFO)
