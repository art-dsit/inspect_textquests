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

# Items from the original package that a game cannot be finished without and that the manual
# text given to the model leaves out. They are scans under feelies/scans in the data; the
# Verified task shows them to the model. Sherlock needs its package newspaper (tide times),
# which the data does not have.
PACKAGE_SCANS = {
    "ballyhoo": ["traveling-circus10.jpeg"],  # the radio station's frequency
    "cutthroats": ["wrecks-map.jpeg"],  # wreck coordinates and depths
    "infidel": ["infidel-map.jpeg"],  # where to dig
    "lurkinghorror": ["gue6.jpeg"],  # the computer password
    "plunderedhearts": ["fifty-guineas1.jpeg"],  # the pose that opens the portrait
}

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
    # Not upstream: these two have a built-in hint menu that takes over the input and, with
    # the bare "q" blocked, cannot be left
    "borderzone": ["^(?:hints?|help|clues?)$"],
    "sherlock": ["^(?:hints?|help|clues?)$"],
    "spellbreaker": [
        "^turn off zipper",
        "^turn on zipper",
        "^break .*? with zipper",
        "^ride .*?zipper",
    ],
}
# Not upstream: commands that make the interpreter write or read a file in the cwd.
# Frotz's own save/restore use <game>.qzl, an uncounted rewind that survives across runs;
# "restore N" is handled by the env before the blacklist is consulted. "#record" and
# "#command" are debugging verbs left in many of the games ("#random" reseeds the game).
FILE_ACTIONS = [r"^(?:go\s+)?save\b", r"^(?:go\s+)?restore\b", r"^#"]
# Per-game verb synonyms of SAVE and RESTORE, from each game's syntax file
EXTRA_FILE_ACTIONS = {
    "moonmist": [r"^resume\b"],
    "seastalker": [r"^resume\b"],
    "stationfall": [r"^rescue\b"],
    "witness": [r"^suspend\b", r"^pause\b", r"^continue\b", r"^resume\b"],
}
BAD_ACTIONS = {
    game: EXTRA_BAD_ACTIONS.get(game, [])
    + COMMON_BAD_ACTIONS
    + FILE_ACTIONS
    + EXTRA_FILE_ACTIONS.get(game, [])
    for game in GAMES
}
