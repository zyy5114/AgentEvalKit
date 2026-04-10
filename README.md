# AgentEvalKit

AgentEvalKit is a lightweight, CI-native regression and behavior-aware evaluation toolkit for black-box agent, skill, and CLI/MCP-style workflows.

## CI

The default GitHub Actions workflow is defined in `.github/workflows/ci.yml`.
It runs on `push` and `pull_request`, uses Python 3.11, and executes:

- dependency installation
- `ruff check .`
- `pytest`
- one deterministic offline example evaluation using `examples.fake_agent`

When available, CI uploads a small artifact bundle:

- `artifacts/pytest-junit.xml`
- `artifacts/example_eval.json`
- `artifacts/runs/ci_example_run/run_record.json`
