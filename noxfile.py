"""Nox automation for prepmd."""

import nox

nox.options.sessions = ["test", "lint", "type", "docs"]


@nox.session(name="test")
def test(session: nox.Session) -> None:
    """Run pytest with coverage."""
    session.run("pixi", "run", "-e", "test", "test", external=True)


@nox.session(name="lint")
def lint(session: nox.Session) -> None:
    """Run ruff and pre-commit hooks."""
    session.run("pixi", "run", "-e", "lint", "lint", external=True)


@nox.session(name="type")
def type_check(session: nox.Session) -> None:
    """Run basedpyright and typeguard checks."""
    session.run("pixi", "run", "-e", "type", "type", external=True)


@nox.session(name="docs")
def docs(session: nox.Session) -> None:
    """Build Sphinx documentation."""
    session.run("pixi", "run", "-e", "docs", "docs", external=True)


@nox.session(name="dev")
def dev(session: nox.Session) -> None:
    """Validate development environment."""
    session.run("pixi", "run", "-e", "dev", "dev", external=True)
