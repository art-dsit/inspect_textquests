"""Download and cache the TextQuests game data.

The upstream harness ships a single zip on Hugging Face containing, per game, the
Jiminy-Cricket recompiled Z-machine file (which emits the annotation markers the
environment relies on), the annotations CSV, the walkthrough, the feelies and the
InvisiClues. Stock Infocom game files will not work.
"""

import fcntl
import hashlib
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DATA_REVISION = "be34a3a9821ba2dd4eb46096a55e9062f6b6d1db"
DATA_URL = f"https://huggingface.co/datasets/justinphan3110/textquests/resolve/{DATA_REVISION}/textquests_data.zip"
DATA_SHA256 = "2a3c696024abe0fe61f27cb451c45413a1f43213358b169ebaeeac1f45359c04"

# Top-level directory inside the zip
ZIP_ROOT = "textquests"

CACHE_ENV_VAR = "INSPECT_TEXTQUESTS_CACHE"


def cache_dir() -> Path:
    override = os.environ.get(CACHE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "inspect_textquests"


def data_dir() -> Path:
    """Directory containing one sub-directory per game plus game_progress.json."""
    return cache_dir() / DATA_REVISION / ZIP_ROOT


def ensure_data() -> Path:
    """Return the data directory, downloading and extracting the zip if needed.

    Safe to call concurrently from many processes: the download is serialised with a file
    lock and the extracted tree is moved into place atomically, so a partial download can't
    be mistaken for a complete one.
    """
    target = data_dir()
    if target.is_dir():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.parent / ".download.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if target.is_dir():
                return target
            _download_and_extract(target)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return target


def _download_and_extract(target: Path) -> None:
    logger.info("Downloading TextQuests game data from %s", DATA_URL)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        zip_path = Path(tmp) / "textquests_data.zip"
        digest = hashlib.sha256()
        with (
            httpx.stream(
                "GET", DATA_URL, follow_redirects=True, timeout=600
            ) as response,
            open(zip_path, "wb") as f,
        ):
            response.raise_for_status()
            for chunk in response.iter_bytes():
                digest.update(chunk)
                f.write(chunk)
        if digest.hexdigest() != DATA_SHA256:
            raise RuntimeError(
                f"TextQuests data zip sha256 {digest.hexdigest()} does not match "
                f"expected {DATA_SHA256}; refusing to use it."
            )
        extract_dir = Path(tmp) / "extracted"
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        shutil.move(str(extract_dir / ZIP_ROOT), str(target))
    logger.info("TextQuests game data extracted to %s", target)


def game_dir(game: str) -> Path:
    return ensure_data() / game


def load_walkthrough(game: str) -> list[str]:
    text = (game_dir(game) / f"{game}_walkthrough.txt").read_text()
    return [line for line in text.split("\n") if line.strip()]
