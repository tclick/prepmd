"""Shared type aliases used across prepmd."""

from pathlib import Path
from typing import Literal

PathLike = str | Path
StringMap = dict[str, str]
Numeric = int | float

StructureFormat = Literal["pdb", "mmcif"]
