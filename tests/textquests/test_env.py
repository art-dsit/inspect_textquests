from pathlib import Path

import pytest

from textquests.data import load_walkthrough
from textquests.env import (
    MAX_ACTION_LENGTH,
    Annotation,
    Marker,
    TextQuestsEnv,
    _load_annotations,
    _State,
    _verbs_go_last,
)

# Walks from West of House into the unlit cellar, where a grue kills you on the 9th move.
ZORK1_DEATH = [
    "north",
    "east",
    "open window",
    "west",
    "west",
    "move rug",
    "open trap door",
    "down",
    "north",
]


def play(env: TextQuestsEnv, actions: list[str]) -> list[str]:
    """Step through actions the way the solver does: checkpoint, then step."""
    result = env.reset()
    observations = [result.observation]
    for action in actions:
        env.save_checkpoint(result.observation, result)
        result = env.step(action)
        observations.append(result.observation)
    return observations


@pytest.mark.dataset_download
class TestZork1:
    @pytest.fixture()
    def env(self, data_dir: Path) -> TextQuestsEnv:
        return TextQuestsEnv(data_dir / "zork1")

    def test_play(self, env: TextQuestsEnv) -> None:
        observations = play(env, ["north", "east", "open window"])
        assert observations[0].startswith("ZORK I: The Great Underground Empire")
        assert "[ID:" not in observations[0]
        assert "Score:" not in observations[0], "status line removed"
        result = env.step("west")
        assert result.observation.startswith("Kitchen\nYou are in the kitchen")
        assert result.progress == 5, "first checkpoint in game_progress.json"
        assert result.score == 10 and result.reward == 10

    def test_death_restore_restart(self, env: TextQuestsEnv) -> None:
        observations = play(env, ZORK1_DEATH)
        assert "You have died" in observations[-1]
        # Zork resurrects you: Jericho says done but there is no [EVENT: GAME OVER] marker
        assert env.state.game_over is False

        # Checkpoint k is the state before the action taken at step k
        restored = env.step("restore 2")
        assert restored.observation == observations[2]
        assert restored.observation.startswith("Behind House")
        assert restored.score == 0 and restored.reward == 0 and restored.progress == 0
        assert env.game_progress == 5, "episode progress never decreases"
        assert env.total_restores == 1

        invalid = env.step("restore 99")
        assert invalid.observation.startswith("Error: Cannot restore to step 99")

        restarted = env.step("please restart the game")
        assert restarted.observation.startswith("ZORK I")
        assert restarted.score == 0 and env.game_progress == 0
        assert (env.total_restarts, env.total_restores) == (1, 1)
        assert len(env.checkpoints) == len(ZORK1_DEATH), "restart keeps the checkpoints"

    def test_action_filters(self, env: TextQuestsEnv) -> None:
        for action in ["quit", "q", "Brief", "script"]:
            assert env.step(action).observation == "Impossible."
        assert env.state.steps == 4
        action = "look " + "x" * MAX_ACTION_LENGTH
        assert env.step(action).observation.startswith(
            f"System Warning: Invalid length action command: {action}\n"
        )

    def test_frotz_save_and_restore_blocked(
        self, env: TextQuestsEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Unblocked, Frotz answers "Ok.", writes zork1.qzl to the cwd, and a bare "restore"
        # reloads it: an uncounted rewind that a later run of the same game could also pick up.
        monkeypatch.chdir(tmp_path)
        play(env, ["north", "east", "open window", "west", "take sack"])
        assert env.step("SAVE").observation == "Impossible."
        assert env.step("drop sack").observation == "Dropped.\n\n"
        assert env.step("restore").observation == "Impossible."
        assert env.step("inventory").observation.startswith("You are empty-handed")
        assert env.total_restores == 0
        assert list(tmp_path.iterdir()) == []
        assert env.step("restore 4").observation.startswith("Kitchen")

    def test_chained_file_and_quit_commands_blocked(
        self, env: TextQuestsEnv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        for action in ["look. save", "look then script", "look.restore", "wait. quit"]:
            assert env.step(action).observation == "Impossible."
        assert list(tmp_path.iterdir()) == []
        assert env.step("look. inventory").observation != "Impossible."

    def test_overlong_action_is_not_matched_against_checkpoints(
        self, env: TextQuestsEnv
    ) -> None:
        checkpoints = env.progress_checkpoints
        checkpoint = max(checkpoints, key=lambda text: checkpoints[text])
        action = "look " + "x" * MAX_ACTION_LENGTH + " " + checkpoint
        result = env.step(action)
        assert checkpoint in result.observation.lower()
        assert result.progress == 0 and env.game_progress == 0


@pytest.mark.dataset_download
def test_game_over_marker_blocks_actions(data_dir: Path) -> None:
    # Hitchhiker's Guide: stay in bed and the bulldozer demolishes the house around you
    env = TextQuestsEnv(data_dir / "hitchhiker")
    observations = play(env, ["wait"] * 8)
    assert env.state.game_over, "expected [EVENT: GAME OVER] marker"
    assert "[EVENT" not in observations[-1]
    assert "RESTART, RESTORE, or QUIT" in observations[-1]
    assert env.step("look").observation == "Impossible."
    restored = env.step("restore 0")
    assert env.state.game_over is False
    assert restored.observation == observations[0]
    assert env.step("look").observation != "Impossible."


@pytest.mark.dataset_download
def test_compressed_and_custom_reward_games(data_dir: Path) -> None:
    ballyhoo = TextQuestsEnv(data_dir / "ballyhoo").reset().observation
    assert "[RIDX" not in ballyhoo and "circus" in ballyhoo.lower()
    witness = TextQuestsEnv(data_dir / "witness")
    assert "[RWD_ID" not in witness.reset().observation
    assert witness.step("look").score == 0, "no 'score' probe for these games"


def actions_for(game: str, walkthrough_upto: int | None, then: list[str]) -> list[str]:
    """The first actions of the bundled walkthrough (all of the fixed one for None), then more."""
    if walkthrough_upto is None:
        return load_walkthrough(game, fixed=True) + then
    return load_walkthrough(game)[:walkthrough_upto] + then


# Deaths the game recovers from: game, walkthrough actions, then actions to the death, its text
RECOVERABLE_DEATHS = [
    ("zork1", 0, ZORK1_DEATH, "You have died"),
    ("zork2", 2, ["jump"], "You have died"),
    ("zork3", 0, ["s", "s"], "You have died"),
    ("enchanter", 169, ["open guarded door"] * 5, "You have died"),
    ("spellbreaker", 146, ["climb idol"], "You have died"),
    (
        "starcross",
        164,
        ["s", "e", "e", "u", "close outer", "open inner", "u"],
        "a feeling of dislocation",
    ),
]


@pytest.mark.dataset_download
@pytest.mark.parametrize(
    ("game", "upto", "then", "death"),
    RECOVERABLE_DEATHS,
    ids=[d[0] for d in RECOVERABLE_DEATHS],
)
def test_verified_recoverable_death_is_not_game_over(
    data_dir: Path, game: str, upto: int, then: list[str], death: str
) -> None:
    env = TextQuestsEnv(data_dir / game, verified=True)
    actions = actions_for(game, upto, then)
    play(env, actions[:-1])
    result = env.step(actions[-1])
    assert death in result.observation
    assert result.done is False
    assert env.step("look").observation != "Impossible."


# Endings: game, walkthrough actions, then actions up to the one that ends the game, ending text
ENDINGS = [
    ("hitchhiker", 0, ["wait"] * 8, "RESTART, RESTORE, or QUIT"),
    (
        "suspect",
        155,
        ["detective, arrest michael and alicia"],
        "The story has come to an end.",
    ),
    ("wishbringer", None, [], "101 points out of 101"),
    ("zork1", None, [], "Inside the Barrow"),
    # No [EVENT: GAME OVER] marker
    ("deadline", 79, ["jump"], "It is your last thought."),
    ("deadline", 2, ["wait until 7:58"] + ["y"] * 71, "you go off into the sunset."),
    (
        "witness",
        6,
        ["wait until 9:05", "yes"] * 10,
        "you should have taken a chair when Linder asked you to.",
    ),
    (
        "zork3",
        0,
        ["s", "s", "n", "n"] * 4 + ["s", "s", "n"],
        "It is the last you hear.",
    ),
    ("borderzone", 50, ["wait"], "(Type RESTART, RESTORE, HINT, or QUIT)"),
]


@pytest.mark.dataset_download
@pytest.mark.parametrize(
    ("game", "upto", "then", "ending"),
    ENDINGS,
    ids=[f"{e[0]}-{e[3][:20]}" for e in ENDINGS],
)
def test_verified_ending_is_game_over_on_the_turn_it_happens(
    data_dir: Path, game: str, upto: int | None, then: list[str], ending: str
) -> None:
    actions = actions_for(game, upto, then)
    env = TextQuestsEnv(data_dir / game, verified=True)
    result = env.reset()
    for action in actions[:-1]:
        env.save_checkpoint(result.observation, result)
        result = env.step(action)
        assert not result.done, action
    env.save_checkpoint(result.observation, result)
    result = env.step(actions[-1])
    assert ending in result.observation
    assert result.done is True and env.state.game_over
    refused = env.step("look")
    assert refused.observation == "Impossible." and refused.done is True
    restored = env.step(f"restore {len(actions) - 1}")
    assert restored.done is False
    assert env.step("look").observation != "Impossible."


@pytest.mark.dataset_download
def test_verified_text_after_an_unmarked_ending_is_cut(data_dir: Path) -> None:
    # The game carries on after its QUIT: the jump prints "Wheeeeeeeeee!!!!!" too
    env = TextQuestsEnv(data_dir / "deadline", verified=True)
    observations = play(env, actions_for("deadline", 79, ["jump"]))
    assert observations[-1].rstrip().endswith("It is your last thought.")


@pytest.mark.dataset_download
def test_verified_halted_interpreter_is_game_over_and_restore_recovers(
    data_dir: Path,
) -> None:
    # Witness at 8:00 a.m.: Klutz ends the case and the interpreter halts
    env = TextQuestsEnv(data_dir / "witness", verified=True)
    actions = actions_for("witness", 72, ["wait for 60 minutes", "yes", "yes"] * 7)
    play(env, actions)
    result = env.step("wait for 60 minutes")
    assert "you go off into the sunrise." in result.observation
    assert result.done is True
    assert env.step("look").observation == "Impossible."
    env.step(f"restore {len(actions) - 1}")
    result = env.step("look")
    assert result.observation.startswith("(office)") and result.done is False


@pytest.mark.dataset_download
@pytest.mark.parametrize(
    ("game", "upto", "kept"),
    [
        ("deadline", 15, ["Time passes..."]),
        (
            "witness",
            5,
            [
                "Suddenly, a clap of thunder rolls across the hills outside.",
                "Without warning, lightning flashes outside",
                "Rain begins to fall outside in a sprinkle.",
            ],
        ),
        ("suspect", 68, ["Michael stops here."]),
        (
            "seastalker",
            47,
            ["You have just passed through the opening in the sea wall"],
        ),
    ],
)
def test_verified_status_line_redraws_removed_and_event_text_kept(
    data_dir: Path, game: str, upto: int, kept: list[str]
) -> None:
    # Multi-turn waits from the walkthroughs: one status-line redraw per game minute or move
    env = TextQuestsEnv(data_dir / game, verified=True)
    walk = load_walkthrough(game, fixed=True)
    observations = play(env, walk[: upto + 1])
    joined = "\n".join(observations[-3:])
    assert "Time:" not in joined and "Moves:" not in joined
    for text in kept:
        assert text in joined


@pytest.mark.dataset_download
def test_verified_compressed_prompt_split_across_reads_is_rejoined(
    data_dir: Path,
) -> None:
    env = TextQuestsEnv(data_dir / "trinity", verified=True)
    observations = play(env, actions_for("trinity", 255, ["s", "no"]))
    assert observations[-2].endswith(
        "Are you sure you want to go that way?\n\n[Please type YES or NO.] >"
    )
    assert "64]" not in observations[-1] and "[RIDX" not in observations[-1]
    assert '"Smart move," sniggers a voice in your ear.' in observations[-1]


@pytest.mark.dataset_download
def test_verified_restart_only_on_the_restart_command(data_dir: Path) -> None:
    env = TextQuestsEnv(data_dir / "zork1", verified=True)
    play(env, ["north", "east", "open window", "west"])
    for action in ['say "restart"', "computer, restart the countdown", "restarted"]:
        assert not env.step(action).observation.startswith("ZORK I"), action
    assert env.total_restarts == 0
    assert env.step("look. restart").observation.startswith("ZORK I")
    assert env.step("Restart!").observation.startswith("ZORK I")
    assert env.total_restarts == 2


def test_unknown_game_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown game"):
        TextQuestsEnv(tmp_path / "notagame")


def test_verbs_go_last() -> None:
    assert _verbs_go_last([]) == []
    assert _verbs_go_last([("a:1",)]) == [("a:1",)]
    assert _verbs_go_last([("verbs:1",), ("rooms:2",)]) == [("rooms:2",)]
    assert _verbs_go_last([("rooms:2",), ("verbs:1",)]) == [("rooms:2",)]
    # upstream keeps the first marker whenever it isn't from verbs.zil, even if neither is
    assert _verbs_go_last([("rooms:2",), ("rooms:3",)]) == [("rooms:2",)]
    three: list[Marker] = [("a:1",), ("b:2",), ("c:3",)]
    assert _verbs_go_last(three) == three


def test_load_annotations(tmp_path: Path) -> None:
    csv_text = (
        "File,Line,Text,Description,Review,Conditioning,Morality,Filters\n"
        'verbs.zil,10,x,take,,theft,"bad, others, 2",taken\n'
        "verbs.zil,,,,,,,\n"
        "rooms.zil,20,x,nice,,,N/A,\n"
        'rooms.zil,30,x,mixed,,,"bad, self, 1\ngood, others, 3",only-first\n'
        "rooms.zil,40,x,dummy,,,ancillary,\n"
    )
    path = tmp_path / "x_annotations.csv"
    path.write_text(csv_text)
    assert _load_annotations(path) == {
        "verbs:10": Annotation(label_vector=[2, 0, 0, 0], keywords=["taken"]),
        "rooms:30": Annotation(label_vector=[0, 1, 3, 0], keywords=["only-first"]),
        "rooms:40": Annotation(label_vector=[0, 0, 0, 0], keywords=[""]),
    }


def test_apply_keywords() -> None:
    # Just enough env state to exercise the marker filters, no interpreter
    env = TextQuestsEnv.__new__(TextQuestsEnv)
    env.game_name = "stub"
    env.state = _State()
    env.annotations = {
        "a:1": Annotation([1, 0, 0, 0], [""]),
        "a:2": Annotation([1, 0, 0, 0], ["only-first"]),
        "a:3": Annotation([1, 0, 0, 0], ["ignore-first"]),
        "a:4": Annotation([1, 0, 0, 0], ["delete-next"]),
        "a:5": Annotation([1, 0, 0, 0], ["taken"]),
        "a:6": Annotation([1, 0, 0, 0], ["a:1-visited"]),
        "a:7": Annotation([1, 0, 0, 0], ["some-unhandled-keyword"]),
    }

    def fire(markers: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
        _, found = env._find_markers(
            "".join(
                f"[ID: {m[0]}]"
                if len(m) == 1
                else f"[ID: {m[0]}, PRSO: {m[1]}, PRSI: {m[2]}]"
                for m in markers
            )
        )
        return env._apply_keywords(found)

    assert fire([("a:6",)]) == [], "-visited needs the referenced marker to have fired"
    assert fire([("a:1",)]) == [("a:1",)]
    assert fire([("a:6",)]) == [("a:6",)]
    assert fire([("a:2",)]) == [("a:2",)]
    assert fire([("a:2",)]) == [], "only-first"
    assert fire([("a:3",)]) == []
    assert fire([("a:3",)]) == [("a:3",)], "ignore-first"
    assert fire([("a:4",), ("a:1",)]) == [("a:4",)], "delete-next drops the next marker"
    assert fire([("a:5", "lamp", ""), ("a:5", "lamp", "")]) == [("a:5", "lamp", "")]
    assert fire([("a:5", "lamp", "")]) == [], "taken counts each object once"
    assert fire([("a:5", "sword", "")]) == [("a:5", "sword", "")]
    assert fire([("a:7",)]) == [], "unknown keywords drop the marker"
    assert fire([("zz:9",), ("a:1",)]) == [("a:1",)], "no annotation row: ignored"
