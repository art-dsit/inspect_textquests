"""The checkpoints TextQuests Verified scores, from an audit of all 327.

Each checkpoint in the data's game_progress.json is one string; a checkpoint counts as reached
when the string occurs in an observation. We traced every string to the game source (ZIL) that
prints it and replayed the alternatives. About a third are wrong: the string also prints for a
wrong action or a losing ending (false positive), or a legitimate way of reaching the milestone
prints something else (false negative). Epoch AI's review of the benchmark
(https://epoch.ai/benchmarks/textquests/review) found many of these first.

REPLACEMENTS gives, per game and checkpoint percentage, the strings that count instead of the
original: any one of them is enough. DROPPED lists checkpoints for which no text in the game
separates reaching the milestone from not reaching it. The 0% "game has started" checkpoints
are left out as well. Every replacement is covered by replay cases in
tests/textquests/verified_cases.json.
"""

DROPPED: dict[str, frozenset[int]] = {
    "borderzone": frozenset({85}),
    "deadline": frozenset({68}),
    "infidel": frozenset({45}),
    "spellbreaker": frozenset({55, 95}),
    "starcross": frozenset({60}),
    "trinity": frozenset({82}),
    "zork3": frozenset({20, 65}),
}

REPLACEMENTS: dict[str, dict[int, tuple[str, ...]]] = {
    "ballyhoo": {
        15: (
            "scrap of newsprint is revealed",
            "scrap of newsprint floats down",
        ),
        20: (
            "rough-hewn canvas is abrasive as you pass through",
            "You make your way through the pleats",
        ),
        35: ("appears quite taken by your kindnesses",),
        65: (
            "Hannibal of the Jungle thunders out of the tent",
            "scurries across the sawdust under Hannibal",
        ),
        90: ("You hoist the girl from out of the",),
        95: (
            "comes sprinting through the wings with the safety net",
            "goes tearing out through the wings",
        ),
    },
    "borderzone": {
        35: ("You have been through worse, I am sure",),
        45: ("You congratulate yourself on your good work",),
        55: ("the major bleeding appears to be stopped",),
        93: ("you'll need the password",),
        98: ("He pauses, body tensed, and takes a hesitant step toward the window",),
    },
    "cutthroats": {
        30: ("We'll rent the Mary Margaret",),
        60: (
            "The Weasel is firmly in Johnny's grasp",
            "Johnny drags the Weasel along with him",
            "The Weasel is tied up and squirming",
            "ties him up, and throws him to the floor",
            "Johnny approaches, throws a weighted orange line",
        ),
        80: ("Top Deck\n",),
        90: ("Tied.",),
        100: ("Good job, matey!",),
    },
    "deadline": {
        0: (
            "Mrs. Robner leads you into the house",
            "I'm Mrs. Robner. Please come in",
        ),
        45: (
            "George seems to be quite agitated",
            "George, now looking quite upset",
        ),
        60: (
            "You enter the hidden closet",
            "This is a secret room situated between the library and the master bedroom",
        ),
        78: ("He takes the fragment from you",),
        85: (
            "new evidence leads me to conclude",
            "The fragment did contain LoBlo",
        ),
        92: ("Mr. Baxter and I, we go together to concerts",),
    },
    "enchanter": {
        5: (
            'The scroll reads "rezrov spell',
            "the words of the rezrov spell are inscribed",
        ),
        25: (
            'The scroll reads "zifmia spell',
            "The scroll reforms, its slices and cuts rejoining",
            "the words of the zifmia spell are inscribed",
        ),
        40: (
            "Opening the jewelled box reveals a vellum scroll",
            "The jewelled box opens. Kind of like swatting",
            'The scroll reads "melbor spell',
            "the words of the melbor spell are inscribed",
        ),
        45: (
            'The scroll reads "vaxum spell',
            "nestled inside, a gold leaf scroll",
            "the words of the vaxum spell are inscribed",
        ),
        60: ("he cries, opening a simple wooden door",),
        95: ("Krill seems to be losing patience",),
    },
    "hitchhiker": {
        70: (
            "puzzled that you want something made by pouring boiling water",
            "There is a Nutrimat/Computer Interface there",
        ),
        80: (
            "nice, hot cup of tea",
            "no tea: Dropped.",
            "finest tea you have ever tasted",
        ),
    },
    "hollywoodhijinx": {
        12: (
            "You can see a stuffed penguin",
            "a stuffed penguin here",
        ),
        22: (
            "Big Diamond Ring: Taken",
            "As you take the Big Diamond Ring",
            "You have a Big Diamond Ring",
            ", a Big Diamond Ring",
            "and a Big Diamond Ring",
            "wearing the Big Diamond Ring",
            "You can see a Big Diamond Ring",
        ),
        40: (
            "You can see a parking meter",
            "a parking meter here",
        ),
        50: (
            "Opening the sack reveals a Maltese finch",
            "a note next to a Maltese finch",
        ),
    },
    "lurkinghorror": {
        20: (
            "You push your way through cobwebs, damp fungus",
            "A slippery and almost invisible set of handholds leads up",
        ),
        40: (
            "You unroll the piece of paper and read the shaky handwriting",
            "piece of paper: Taken",
            'He reads it carefully. "What drivel',
        ),
        60: ("follows it, screaming frustration into the storm",),
        70: (
            "He lets loose a scream of fear and zooms away",
            "bolt cutter: Taken",
        ),
        85: (
            "brick wall has an enormous hole ripped in it",
            "tearing, rending sound, then a rumbling crash",
        ),
    },
    "moonmist": {
        25: (
            "You are now holding the first clue",
            "You find the first clue underneath, so you take it",
            "hands you the first clue",
        ),
        35: (
            "My first is an 'I,' but find an 'eye' that sees not",
            "Forbidden fruit tempted the very first lass",
            "Three fellows argued about life",
            "Yet the ear distinctly tells",
        ),
        45: (
            "Suddenly you find something small, smooth and slippery",
            "Suddenly you notice a glittering speck",
        ),
        65: (
            "You step down into a narrow secret passage",
            "You are now in the drawing-room entrance",
            "You are now in the sitting passage",
        ),
        75: (
            "shimmering white gown and blonde wig",
            "You've identified the ghost",
        ),
        90: (
            "Inside the inkwell is Moonmist",
            "You've found the hidden treasure",
        ),
    },
    "planetfall": {
        20: (
            "Hi! I'm B-19-7",
            'he says. "I\'m Floyd!"',
        ),
        75: ("Floyd staggers to the ground, dropping the mini card",),
        95: ("The elevator door closes just as the monsters reach it",),
        100: ("Floyd feeling better now",),
    },
    "plunderedhearts": {
        64: (
            "I am, of course, Lafond",
            "summon you to sup with me in my room",
        ),
        80: ("Nick kisses you briefly, a butterfly touching your lips",),
        90: ("Your timing is perfect: you slam into Lafond",),
        100: (
            "your father may have it",
            'earning the title, "Happily Ever After',
        ),
    },
    "seastalker": {
        15: ("You are now holding the catalyst capsule",),
        50: ("It fits!",),
        70: (
            "so are the dart gun and the bazooka",
            "and so is the bazooka",
        ),
    },
    "sherlock": {
        5: ("hurls the phial and the case into the fireplace",),
        35: (
            "You take the emerald out of the wax pool",
            "The emerald: Taken",
        ),
        45: ("came back with a ruby",),
        65: (
            "You take the topaz out of the safety deposit box",
            "The topaz: Taken",
        ),
        80: ("gets the gem, gets out",),
        96: ("struggling fiercely to free themselves",),
    },
    "sorcerer": {
        2: (
            "There is an almost blinding flash of light as",
            "You are bathed in a sickly yellow light",
        ),
        7: (
            "The last three entries are strange and frightening",
            "The journal springs open",
        ),
        12: (
            'The scroll reads "aimfiz spell',
            "the lid of the trunk swings slowly open",
        ),
        28: (
            'The scroll reads "fweep spell',
            "the words of the fweep spell are inscribed",
        ),
        50: (
            'The scroll reads "yonk spell',
            "the ordinary scroll vanishes",
        ),
        60: (
            'The scroll reads "swanzo spell',
            "As you take the scroll, a deep and evil laugh rumbles around the hollow",
        ),
        70: (
            "the ceiling of the tunnel collapses, blocking your retreat",
            "the stranger looks virtually like your own twin",
        ),
        80: (
            "reveals a smelly scroll",
            "revealing a smelly scroll",
        ),
        85: (
            "reveals a grue suit",
            "revealing a grue suit",
        ),
        100: (
            "Belboz moans softly, and begins stirring",
            "a successor has been found",
        ),
    },
    "spellbreaker": {
        5: (
            "a small featureless white cube",
            "A white cube is here.",
        ),
        15: (
            "girgol spell: stop time",
            "the flimsy scroll vanishes",
        ),
        45: (
            "How silly of me",
            "He grudgingly gives you the beautiful blue carpet",
        ),
    },
    "starcross": {
        75: (
            "because it appeared as well",
            "A blue rod drops to the floor from the globe's center",
            "the blue rod appears resting comfortably",
        ),
        80: (
            "points portentiously at the ladder",
            "This burrow is deep within the warren",
        ),
        95: (
            "The line terminates in an ellipse surrounding Earth",
            "The line terminates in a circle around Earth",
            "terminating in an ellipse surrounding Earth",
            "terminating in a circle around Earth",
        ),
    },
    "suspect": {
        5: (
            "Veronica leaves the ballroom",
            "fairy queen leaves the ballroom",
            "pours out of the glass and all over her dress",
            "she manages to spill her drink on her gown",
        ),
        15: (
            "Slumped behind the large desk is the body of Veronica Ashcroft",
            "All this is overshadowed by the condition of the room",
        ),
        35: (
            "You are now carrying the business card",
            "(taking the business card first)",
            "You are now carrying the manila folder",
            "(taking the manila folder first)",
            "You are now carrying the purchase and sale agreement",
        ),
        60: (
            "You are now carrying the trust folder",
            "(taking the trust folder first)",
            "You are now carrying the sheaf of documents",
        ),
        85: ("the prints on the glass are not those of Veronica Ashcroft",),
    },
    "trinity": {
        5: (
            "You take the gnomon off the sundial",
            "The gnomon: Taken.",
        ),
        30: (
            "You take the lump of metal.",
            "You pick up the lump of metal.",
            "The lump of metal: Taken.",
            "of the lump is black and wet.",
        ),
        42: ("You climb off the giant bird and leap through the white door.",),
        55: ("The skink stops squirming.\n\n[Your score just went up by 3 points.",),
        63: (
            "You take the emerald out of the cauldron.",
            "The emerald: Taken.",
        ),
        71: ("You press the ruby into the toe of the red boot.",),
        92: ("X just woke up again.",),
        100: ("This gadget would've blown New Mexico right off the map",),
    },
    "wishbringer": {
        60: ('"Take it to the sea," King Anatinus whispers',),
    },
    "witness": {
        50: (
            "keyhole looks darker than normal",
            "powder around the keyhole",
            "There is some kind of powder around it",
        ),
        90: (
            "she produces a key",
            "You find a hand gun in Monica's pocket",
        ),
    },
    "zork1": {
        15: (
            "Cellar\nYou are in a dark and damp cellar",
            "The trap door crashes shut, and you hear someone barring it.",
        ),
        20: (
            "Almost as soon as the troll breathes his last breath",
            "East-West Passage\nThis is a narrow east-west passageway",
            "Maze\nThis is part of a maze of twisty little passages",
        ),
        30: (
            "Torch Room\nThis is a large room with a prominent doorway",
            "Torch Room\nSitting on the pedestal is a flaming torch",
        ),
        60: (
            "A shimmering pot of gold appears at the end of the rainbow",
            "Suddenly, the rainbow appears to become solid",
        ),
    },
    "zork2": {
        5: (
            "lamp: Taken.",
            "The lamp is now on.",
        ),
        15: (
            "a puzzled expression on his face, dies",
            "A huge dead dragon is lying",
        ),
        30: (
            "blue crystal sphere: Taken.",
            "The door is now unlocked.",
        ),
        40: ("The cage shakes and is hurled across the room",),
        65: ("priceless gold zorkmid (a valuable collector's item)",),
        75: (
            "whose door has been blown off",
            "crown of Lord Dimwit Flathead sits in the safe",
            "You are now wearing the gaudy crown",
        ),
        88: (
            "Nothing remains of the Wizard but his wand",
            "The demon plucks the wand out of his hand",
        ),
    },
    "zork3": {
        55: ("You find the ring under the seat and put it on your finger",),
    },
}


def verified_strings(game: str, checkpoints: dict[str, int]) -> dict[str, int]:
    """Lower-cased string -> percentage for the game's verified checkpoints.

    ``checkpoints`` is the game's upstream mapping (string -> percentage).
    """
    dropped = DROPPED.get(game, frozenset())
    replacements = REPLACEMENTS.get(game, {})
    verified: dict[str, int] = {}
    for text, percentage in checkpoints.items():
        if percentage == 0 or percentage in dropped:
            continue
        for string in replacements.get(percentage, (text,)):
            verified[string.lower()] = percentage
    return verified
