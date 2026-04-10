"""Smoke tests for the AgentEvalKit CLI."""

from typer.testing import CliRunner

from agent_evalkit.cli import app


def test_cli_starts_with_help() -> None:
    """The CLI should start and expose top-level help."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "diff" in result.output
    assert "validate" in result.output
