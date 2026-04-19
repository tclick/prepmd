"""Sphinx configuration for prepmd."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prepmd.tools.generate_schema import write_reference, write_schema  # noqa: E402

project = "prepmd"
copyright = "2026, tclick"
author = "tclick"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = os.environ.get("SPHINX_THEME", "sphinx_rtd_theme")
html_static_path = ["_static"]

DOCS_DIR = Path(__file__).resolve().parent
write_schema(DOCS_DIR / "_static" / "prepmd.schema.json")
write_reference(DOCS_DIR / "_generated" / "config_reference_autogen.rst")
