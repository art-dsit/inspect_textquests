from pathlib import Path

import pytest

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
        observations = play(env, ["north", "east", "open window", "west"])
        assert observations[0].startswith("ZORK I: The Great Underground Empire")
        assert "[ID:" not in observations[0]
        assert "Score:" not in observations[0], "status line removed"
        assert observations[-1].startswith("Kitchen\nYou are in the kitchen")
        assert env.game_progress == 5, "first checkpoint in game_progress.json"
        assert env.state.current_score == 10

    def test_death_restore_restart(self, env: TextQuestsEnv) -> None:
        observations = play(env, ZORK1_DEATH)
        assert "You have died" in observations[-1]
        # Zork resurrects you: Jericho says done but there is no [EVENT: GAME OVER] marker
        assert env.state.game_over is False

        # Checkpoint k is the state before the action taken at step k
        restored = env.step("restore 2")
        assert restored.observation == observations[2]
        assert restored.observation.startswith("Behind House")
        assert restored.score == 0 and restored.progress == 0
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
