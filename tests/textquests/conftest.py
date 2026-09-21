from pathlib import Path

import pytest

from textquests.data import ensure_data


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return ensure_data()
