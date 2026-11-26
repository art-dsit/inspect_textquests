import hashlib
import io
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest

from textquests import data


def make_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("textquests/game_progress.json", "{}")
        zf.writestr(
            "textquests/zork1/zork1_walkthrough.txt", "open mailbox\n\nread leaflet\n"
        )
    return buf.getvalue()


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self) -> Iterator[bytes]:
        yield self.payload[:10]
        yield self.payload[10:]


@pytest.fixture()
def fake_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> bytes:
    payload = make_zip()

    @contextmanager
    def fake_stream(*args: Any, **kwargs: Any) -> Iterator[FakeResponse]:
        yield FakeResponse(payload)

    monkeypatch.setattr(httpx, "stream", fake_stream)
    monkeypatch.setenv(data.CACHE_ENV_VAR, str(tmp_path / "cache"))
    return payload


def test_ensure_data_downloads_verifies_and_extracts(
    fake_download: bytes, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "DATA_SHA256", hashlib.sha256(fake_download).hexdigest())
    target = data.ensure_data()
    assert target == tmp_path / "cache" / data.DATA_REVISION / "textquests"
    assert (target / "game_progress.json").read_text() == "{}"
    assert data.load_walkthrough("zork1") == ["open mailbox", "read leaflet"]
    assert not list(target.parent.glob("tmp*")), "temp dirs cleaned up"
    # second call is a no-op
    monkeypatch.setattr(data, "DATA_SHA256", "not-checked-when-cached")
    assert data.ensure_data() == target


def test_ensure_data_rejects_bad_hash(
    fake_download: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "DATA_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="sha256"):
        data.ensure_data()
    assert not data.data_dir().exists(), "nothing left that looks like a cache"
