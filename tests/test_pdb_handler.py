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


def test_validate_pdb_id_rejects_unicode_chars_that_uppercase_to_ascii() -> None:
    with pytest.raises(PDBValidationError):
        validate_pdb_id("\u0131\u0131\u0131\u0131")


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


def test_get_or_download_offline_uses_cached_file_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / "1ABC.pdb"
    cached.write_text("cached", encoding="utf-8")
    handler = PDBHandler(cache_dir=cache_dir, offline=True)

    def should_not_download(*args: object, **kwargs: object) -> str:
        raise AssertionError("network should not be used in offline mode")

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", should_not_download)

    assert handler.get_or_download("1abc") == cached


def test_get_or_download_offline_raises_on_cache_miss(tmp_path: Path) -> None:
    handler = PDBHandler(cache_dir=tmp_path / "cache", offline=True)

    with pytest.raises(PDBDownloadError, match="Offline mode is enabled"):
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


# ---------------------------------------------------------------------------
# mmCIF format support
# ---------------------------------------------------------------------------


def test_cache_path_pdb_format(tmp_path: Path) -> None:
    handler = PDBHandler(cache_dir=tmp_path, structure_format="pdb")
    assert handler.cache_path("1abc") == tmp_path / "1ABC.pdb"


def test_cache_path_mmcif_format(tmp_path: Path) -> None:
    handler = PDBHandler(cache_dir=tmp_path, structure_format="mmcif")
    assert handler.cache_path("1abc") == tmp_path / "1ABC.cif"


def test_get_or_download_mmcif_uses_cached_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / "1ABC.cif"
    cached.write_text("cached_mmcif", encoding="utf-8")
    handler = PDBHandler(cache_dir=cache_dir, structure_format="mmcif")

    assert handler.get_or_download("1abc") == cached


def test_get_or_download_mmcif_uses_correct_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    handler = PDBHandler(cache_dir=cache_dir, retries=1, backoff_seconds=0.0, structure_format="mmcif")
    captured_formats: list[str] = []

    def fake_retrieve(
        self: Any,
        pdb_code: str,
        obsolete: bool,
        pdir: str,
        file_format: str,
        overwrite: bool,
    ) -> str:
        captured_formats.append(file_format)
        path = Path(pdir) / f"{pdb_code.lower()}.cif"
        path.write_text("mmcif_content", encoding="utf-8")
        return str(path)

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", fake_retrieve)

    path = handler.get_or_download("1abc")

    assert captured_formats == ["mmCif"]
    assert path == cache_dir / "1ABC.cif"


def test_get_or_download_mmcif_skips_replace_when_paths_point_to_same_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = cache_dir / "1ABC.cif"
    downloaded = cache_dir / "1abc.cif"
    downloaded.write_text("downloaded", encoding="utf-8")
    try:
        cached.hardlink_to(downloaded)
    except OSError:
        pytest.skip("Filesystem does not support creating hard links for same-file regression test.")
    handler = PDBHandler(cache_dir=cache_dir, retries=1, backoff_seconds=0.0, structure_format="mmcif")
    replaced = {"called": False}

    def fake_retrieve(
        self: Any,
        pdb_code: str,
        obsolete: bool,
        pdir: str,
        file_format: str,
        overwrite: bool,
    ) -> str:
        return str(downloaded)

    original_replace = Path.replace

    def track_replace(self: Path, target: Path) -> Path:
        replaced["called"] = True
        return original_replace(self, target)

    monkeypatch.setattr("prepmd.structure.pdb_handler.PDBList.retrieve_pdb_file", fake_retrieve)
    monkeypatch.setattr(Path, "replace", track_replace)

    path = handler.get_or_download("1abc")

    assert path == cached
    assert replaced["called"] is False


def test_cleanup_cache_removes_cif_files(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "1ABC.pdb").write_text("x", encoding="utf-8")
    (cache_dir / "2DEF.cif").write_text("x", encoding="utf-8")
    handler = PDBHandler(cache_dir=cache_dir)

    removed = handler.cleanup_cache()
    assert removed == 2
    assert not any(cache_dir.iterdir())
