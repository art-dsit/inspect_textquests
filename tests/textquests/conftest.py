from pathlib import Path

import pytest

from textquests.data import ensure_data


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return ensure_data()


@pytest.fixture(autouse=True)
def _logs_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPECT_LOG_DIR", str(tmp_path))
