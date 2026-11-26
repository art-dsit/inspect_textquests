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

# Upstream's blacklist: actions that can hang or break the interpreter, answered
# "Impossible.". Matched case-insensitively against the whole action, as upstream does, except
# in verified mode, where each command of a chained action is checked
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
# Verified only: these two have a built-in hint menu that takes over the input and, with the
# bare "q" blocked, cannot be left
HINT_MENU_ACTIONS = {
    "borderzone": ["^(?:hints?|help|clues?)$"],
    "sherlock": ["^(?:hints?|help|clues?)$"],
}
# Not upstream, and blocked in every command of an action in both modes: commands that make
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
# Everything the verified environment checks in each command of an action
BAD_ACTIONS = {
    game: EXTRA_BAD_ACTIONS.get(game, [])
    + HINT_MENU_ACTIONS.get(game, [])
    + COMMON_BAD_ACTIONS
    + FILE_COMMANDS[game]
    for game in GAMES
}

# Endings that print no [EVENT: GAME OVER] marker, by the end of the text the game prints
# only there. Except in borderzone, whose FINISH waits for a CONTINUE that a failed chapter
# cannot take, each is followed by the Z-machine's QUIT, which this interpreter does not stop
# at: the game carries on as if the ending had not happened. Used by the verified environment.
UNMARKED_ENDINGS: dict[str, tuple[str, ...]] = {
    "borderzone": ("(Type RESTART, RESTORE, HINT, or QUIT)",),
    "deadline": (
        "you go off into the sunset.",  # the 8 pm time limit
        "It is your last thought.",
        "You fall back, into a long silence.",
        "are the last you hear.",
        "remove a gun, and end your life.",
    ),
    "witness": (
        "a two-bit shamus!",
        "you should have taken a chair when Linder asked you to.",
        "sooner or later.",  # arriving too late, or quitting late
    ),
    "zork3": ("It is the last you hear.",),  # the fourth death
}
