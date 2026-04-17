"""Sphinx configuration for prepmd."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
