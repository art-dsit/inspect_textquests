"""Per-game constants, copied from src/game_info.py in centerforaisafety/textquests (MIT)."""

MAX_SCORES: dict[str, int] = {
    "ballyhoo": 205,
    "borderzone": 40,
    "cutthroats": 250,
    "deadline": 17,
    "enchanter": 400,
    "hitchhiker": 410,
    "hollywoodhijinx": 150,
    "infidel": 410,
    "lurkinghorror": 105,
    "moonmist": 23,
    "planetfall": 85,
    "plunderedhearts": 25,
    "seastalker": 105,
    "sherlock": 100,
    "sorcerer": 400,
    "spellbreaker": 600,
    "starcross": 400,
    "stationfall": 80,
    "suspect": 21,
    "trinity": 105,
    "wishbringer": 101,
    "witness": 14,
    "zork1": 360,
    "zork2": 410,
    "zork3": 8,
}

GAMES = sorted(MAX_SCORES)

# Actions that can hang or break the interpreter; matched case-insensitively, answered "Impossible."
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
EXTRA_BAD_ACTIONS = {
    "seastalker": [
        "^(?:walk|go|run|proceed|steed|head|drive) (?!north|south|east|west|down|up|in|out)",
        "^suspend.*",
        "^pause.*",
    ],
    "spellbreaker": [
        "^turn off zipper",
        "^turn on zipper",
        "^break .*? with zipper",
        "^ride .*?zipper",
    ],
}
BAD_ACTIONS = {
    game: EXTRA_BAD_ACTIONS.get(game, []) + COMMON_BAD_ACTIONS for game in GAMES
}
