"""PDB download and cache utilities."""

import re
import time
from pathlib import Path
from typing import Any, cast

from Bio.PDB.PDBList import PDBList
from loguru import logger

from prepmd.exceptions import PDBDownloadError, PDBValidationError
from prepmd.types import StructureFormat

PDB_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{4}$")

_BIOPYTHON_FORMAT: dict[StructureFormat, str] = {"pdb": "pdb", "mmcif": "mmCif"}
_CACHE_EXTENSION: dict[StructureFormat, str] = {"pdb": ".pdb", "mmcif": ".cif"}


def validate_pdb_id(pdb_id: str) -> str:
    """Validate and normalize a PDB ID."""
    if pdb_id != pdb_id.strip():
        raise PDBValidationError("PDB ID must not include leading or trailing whitespace.")
    if not PDB_ID_PATTERN.fullmatch(pdb_id):
        raise PDBValidationError("PDB ID must be exactly 4 alphanumeric characters.")
    return pdb_id.upper()


def prefer_remote_structure_format(configured: StructureFormat) -> StructureFormat:
    """Prefer mmCIF for remote PDB ID downloads."""
    if configured == "pdb":
        return "mmcif"
    return configured


class PDBHandler:
    """Retrieve and cache PDB/mmCIF files from the Protein Data Bank."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
        offline: bool = False,
        structure_format: StructureFormat = "pdb",
    ) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "prepmd" / "pdb"
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.offline = offline
        self.structure_format: StructureFormat = structure_format

    def cache_path(self, pdb_id: str) -> Path:
        """Return cache file path for a PDB ID."""
        normalized = validate_pdb_id(pdb_id)
        ext = _CACHE_EXTENSION[self.structure_format]
        return self.cache_dir / f"{normalized}{ext}"

    def get_or_download(self, pdb_id: str) -> Path:
        """Get a cached structure, downloading it when needed."""
        normalized = validate_pdb_id(pdb_id)
        cached = self.cache_path(normalized)
        if cached.exists():
            logger.info(f"Using cached PDB file for {normalized}: {cached}")
            return cached

        if self.offline:
            raise PDBDownloadError(
                "Offline mode is enabled and the requested PDB is not in cache: "
                f"{normalized} at {cached}. Pre-populate this cache file or choose a cache directory via "
                "--pdb-cache-dir / protein.pdb_cache_dir."
            )

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
                        file_format=_BIOPYTHON_FORMAT[self.structure_format],
                        overwrite=True,
                    ),
                )
                if downloaded_str is None:
                    raise FileNotFoundError(f"Download API returned no file path for {normalized}.")
                downloaded = Path(downloaded_str)
                if not downloaded.exists():
                    raise FileNotFoundError(f"Downloaded file not found for {normalized}.")
                if downloaded != cached:
                    same_file = False
                    if cached.exists():
                        try:
                            same_file = downloaded.samefile(cached)
                        except OSError:
                            same_file = False
                    if not same_file:
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
            for pattern in ("*.pdb", "*.cif"):
                for path in self.cache_dir.glob(pattern):
                    path.unlink()
                    removed += 1
        logger.info(f"Removed {removed} cached PDB file(s) from {self.cache_dir}")
        return removed
