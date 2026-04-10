"""Command-line interface for AgentEvalKit."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="aek",
    help="AgentEvalKit: CI-native regression and behavior-aware evaluation toolkit.",
    no_args_is_help=True,
)


@app.command("run")
def run_command() -> None:
    """Run task evaluations (placeholder)."""
    typer.echo("`aek run` is scaffolded and ready for implementation.")


@app.command("diff")
def diff_command() -> None:
    """Compare baseline and candidate runs (placeholder)."""
    typer.echo("`aek diff` is scaffolded and ready for implementation.")


@app.command("validate")
def validate_command() -> None:
    """Validate specs and outputs (placeholder)."""
    typer.echo("`aek validate` is scaffolded and ready for implementation.")


if __name__ == "__main__":
    app()
