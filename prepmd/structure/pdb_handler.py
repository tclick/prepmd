"""PDB download and cache utilities."""

import re
import time
from pathlib import Path
from typing import Any, cast

from Bio.PDB.PDBList import PDBList
from loguru import logger

from prepmd.exceptions import PDBDownloadError, PDBValidationError

PDB_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{4}$")


def validate_pdb_id(pdb_id: str) -> str:
    """Validate and normalize a PDB ID."""
    if pdb_id != pdb_id.strip():
        raise PDBValidationError("PDB ID must not include leading or trailing whitespace.")
    normalized = pdb_id.upper()
    if not PDB_ID_PATTERN.fullmatch(normalized):
        raise PDBValidationError("PDB ID must be exactly 4 alphanumeric characters.")
    return normalized


class PDBHandler:
    """Retrieve and cache PDB files from the Protein Data Bank."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "prepmd" / "pdb"
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def cache_path(self, pdb_id: str) -> Path:
        """Return cache file path for a PDB ID."""
        normalized = validate_pdb_id(pdb_id)
        return self.cache_dir / f"{normalized}.pdb"

    def get_or_download(self, pdb_id: str) -> Path:
        """Get a cached structure, downloading it when needed."""
        normalized = validate_pdb_id(pdb_id)
        cached = self.cache_path(normalized)
        if cached.exists():
            logger.info(f"Using cached PDB file for {normalized}: {cached}")
            return cached

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                logger.info(f"Downloading PDB {normalized} (attempt {attempt}/{self.retries})")
                pdb_client: Any = PDBList()
                downloaded_str = cast(
                    str | None,
                    pdb_client.retrieve_pdb_file(
                        normalized,
                        obsolete=False,
                        pdir=str(self.cache_dir),
                        file_format="pdb",
                        overwrite=True,
                    ),
                )
                if downloaded_str is None:
                    raise FileNotFoundError(f"Download API returned no file path for {normalized}.")
                downloaded = Path(downloaded_str)
                if not downloaded.exists():
                    raise FileNotFoundError(f"Downloaded file not found for {normalized}.")
                if downloaded != cached:
                    if cached.exists():
                        cached.unlink()
                    downloaded.replace(cached)
                logger.info(f"Downloaded PDB {normalized} to {cached}")
                return cached
            except (OSError, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                sleep_time = min(self.backoff_seconds * (2 ** (attempt - 1)), self.max_backoff_seconds)
                logger.warning(f"PDB download failed for {normalized}: {exc}. Retrying in {sleep_time:.2f}s.")
                time.sleep(sleep_time)
        raise PDBDownloadError(f"Failed to download PDB '{normalized}' after {self.retries} attempts.") from last_error

    def cleanup_cache(self, pdb_id: str | None = None) -> int:
        """Cleanup cached PDB files.

        Returns number of removed files.
        """
        removed = 0
        if pdb_id is not None:
            target = self.cache_path(pdb_id)
            if target.exists():
                target.unlink()
                removed += 1
        else:
            for path in self.cache_dir.glob("*.pdb"):
                path.unlink()
                removed += 1
        logger.info(f"Removed {removed} cached PDB file(s) from {self.cache_dir}")
        return removed
