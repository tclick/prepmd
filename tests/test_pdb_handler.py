from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from prepmd.exceptions import PDBDownloadError, PDBValidationError
from prepmd.structure.pdb_handler import PDBHandler, validate_pdb_id


@given(st.from_regex(r"[A-Za-z0-9]{4}", fullmatch=True))
def test_validate_pdb_id_accepts_4_alnum(pdb_id: str) -> None:
    assert validate_pdb_id(pdb_id) == pdb_id.upper()


INVALID_PDB_ID_STRATEGY = st.one_of(
    st.text(max_size=3),
    st.text(min_size=5, max_size=8),
    st.from_regex(r"[^A-Za-z0-9]{4}", fullmatch=True),
)


@given(INVALID_PDB_ID_STRATEGY)
def test_validate_pdb_id_rejects_invalid_values(pdb_id: str) -> None:
    with pytest.raises(PDBValidationError):
        validate_pdb_id(pdb_id)


def test_get_or_download_uses_cached_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / "1ABC.pdb"
    cached.write_text("cached", encoding="utf-8")
    handler = PDBHandler(cache_dir=cache_dir)

    assert handler.get_or_download("1abc") == cached


def test_get_or_download_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    attempts = {"count": 0}
    cache_dir = tmp_path / "cache"
    handler = PDBHandler(cache_dir=cache_dir, retries=3, backoff_seconds=0.0)

    # Signature intentionally mirrors Bio.PDB.PDBList.retrieve_pdb_file for monkeypatch compatibility.
    def fake_retrieve(
        self: Any,
        pdb_code: str,
        obsolete: bool,
        pdir: str,
        file_format: str,
        overwrite: bool,
    ) -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("temporary failure")
        path = Path(pdir) / f"pdb{pdb_code.lower()}.ent"
        path.write_text("downloaded", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", fake_retrieve)

    path = handler.get_or_download("1abc")

    assert attempts["count"] == 3
    assert path == cache_dir / "1ABC.pdb"
    assert path.read_text(encoding="utf-8") == "downloaded"


def test_get_or_download_raises_after_retries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    handler = PDBHandler(cache_dir=tmp_path / "cache", retries=2, backoff_seconds=0.0)

    # Signature intentionally mirrors Bio.PDB.PDBList.retrieve_pdb_file for monkeypatch compatibility.
    def always_fail(
        self: Any,
        pdb_code: str,
        obsolete: bool,
        pdir: str,
        file_format: str,
        overwrite: bool,
    ) -> str:
        raise OSError("network down")

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", always_fail)

    with pytest.raises(PDBDownloadError):
        handler.get_or_download("1abc")


def test_cleanup_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    for pdb_id in ["1ABC", "2DEF"]:
        (cache_dir / f"{pdb_id}.pdb").write_text("x", encoding="utf-8")
    handler = PDBHandler(cache_dir=cache_dir)

    assert handler.cleanup_cache("1abc") == 1
    assert (cache_dir / "1ABC.pdb").exists() is False
    assert handler.cleanup_cache() == 1
