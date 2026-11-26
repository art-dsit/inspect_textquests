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

# Upstream's blacklist: actions that can hang or break the interpreter, answered
# "Impossible.". Matched case-insensitively against the whole action, as upstream does
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
UPSTREAM_BAD_ACTIONS = {
    game: EXTRA_BAD_ACTIONS.get(game, []) + COMMON_BAD_ACTIONS for game in GAMES
}
# Not upstream, and blocked in every command of an action: commands that make
# the interpreter write or read a file in the cwd. Frotz's own save/restore use <game>.qzl, an
# uncounted rewind that survives across runs; "restore N" is handled by the env before the
# blacklist is consulted. SCRIPT writes a transcript named after the input line. "#record" and
# "#command" are debugging verbs left in many of the games ("#random" reseeds the game).
FILE_ACTIONS = [
    r"^(?:go\s+)?save\b",
    r"^(?:go\s+)?restore\b",
    r"^(?:un)?script",
    r"^#",
]
# Per-game verb synonyms of SAVE and RESTORE, from each game's syntax file
EXTRA_FILE_ACTIONS = {
    "moonmist": [r"^resume\b"],
    "seastalker": [r"^resume\b"],
    "stationfall": [r"^rescue\b"],
    "witness": [r"^suspend\b", r"^pause\b", r"^continue\b", r"^resume\b"],
}
FILE_COMMANDS = {
    game: FILE_ACTIONS + EXTRA_FILE_ACTIONS.get(game, []) for game in GAMES
}
