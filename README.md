# AgentEvalKit

**AgentEvalKit** is a lightweight, CI-native regression and behavior-aware evaluation toolkit for black-box agent, skill, and CLI/MCP-style workflows.

It is designed for a practical engineering question:

> **Did the new version get better or worse, and did the runtime environment change?**

Instead of building another agent application, AgentEvalKit focuses on the infrastructure around agent evaluation:
- declarative task specs
- output validation
- behavior-aware scoring
- normalized traces
- run fingerprinting
- baseline vs candidate diffs
- concise regression reports
- GitHub Actions integration

---

## Why this project exists

Many agent systems can "run," but are still hard to evaluate reliably.

Common problems include:
- a prompt or adapter changes and nobody knows whether quality improved or regressed
- output looks acceptable, but tool usage or intermediate behavior violated constraints
- a score changes, but it is unclear whether the cause was code regression or environment drift
- evaluation exists locally, but is not integrated into CI

AgentEvalKit aims to make these workflows smaller, clearer, and easier to automate.

---

## Current scope

This repository currently includes:

- **YAML Task Specs** for declarative task definitions
- **JSON Schema validation** for structured final outputs
- **Behavior compliance scoring** against executable behavior rules
- **CLI adapter** for subprocess-based black-box tasks
- **Python callable adapter** for local deterministic offline tasks
- **Trace collection and self-validation**
- **Run metadata persistence**
- **Run fingerprint generation**
- **Baseline vs candidate diffing**
- **Markdown regression report generation**
- **GitHub Actions CI**

This is a **v0.1-style engineering prototype** focused on being small, explicit, and testable.

---

## Core ideas

### 1. Declarative task specs
Tasks are defined in YAML with structured fields such as:
- `task_id`
- `description`
- `input`
- `adapter`
- `output_schema`
- `behavior_rules`
- `scorers`

### 2. Behavior-aware evaluation
The toolkit does not only check final output. It can also validate whether execution behavior respected rules such as:
- forbidden tools
- required tool groups
- maximum step count
- maximum tool-call count
- trace required
- timeout budget

### 3. Trace contract
Execution traces are normalized into a small, explicit, versioned schema that supports later scoring and debugging.

### 4. Run fingerprinting
Each run can capture environment and configuration signals such as:
- Python version
- OS
- adapter type/version
- runner version
- dependency metadata hash
- seed
- network enabled flag
- task spec hash
- scorer config hash
- model id when available

This helps distinguish likely **system regression** from likely **environment drift**.

### 5. Regression-first reporting
Given a baseline and a candidate run, AgentEvalKit can compute:
- success rate delta
- score delta
- latency delta
- changed failure cases
- violation distribution changes
- drift hints from fingerprint differences

---

## Repository layout

```text
agent_evalkit/
  specs/         # task spec loading and validation
  runners/       # run record metadata and persistence
  adapters/      # CLI and Python adapters
  scorers/       # schema and behavior scorers
  traces/        # trace collection and validation
  fingerprint/   # environment snapshot and run fingerprint helpers
  diff/          # baseline vs candidate comparison
  reports/       # markdown regression reporting

schemas/         # JSON Schemas
examples/        # deterministic example tasks and fake agent
tests/           # unit and integration tests
docs/            # design notes
.github/workflows/ # CI workflow
```

---

## Quickstart

### Requirements

- Python 3.11

### Install

```bash
python -m pip install -e ".[dev]"
python -m pip install pydantic PyYAML jsonschema
```

### Run tests

```bash
python -m pytest -q
```

### Run lint

```bash
python -m ruff check .
python -m ruff format .
```

### Run pre-commit

```bash
python -m pre_commit run --all-files
```

---

## Minimal examples

### Load a task spec

```python
from agent_evalkit.specs.loader import load_task_spec

spec = load_task_spec("examples/task_echo.yaml")
print(spec.task_id)
print(spec.behavior_rules)
```

### Validate structured output with JSON Schema

```python
import json
from pathlib import Path

from agent_evalkit.scorers.schema_validity import score_schema_validity

schema = json.loads(Path("schemas/extract_output.schema.json").read_text(encoding="utf-8"))
payload = {
    "answer": "Open-source deep research agents are evolving quickly.",
    "citations": [
        {"source_id": "src1", "quote": "example quote"}
    ],
}

result = score_schema_validity(schema=schema, final_output=payload)
print(result)
```

### Run a deterministic local Python agent

```python
from agent_evalkit.adapters.python_adapter import run_python_callable
from examples.fake_agent import fake_local_agent, offline_demo_inputs

payload = offline_demo_inputs()[0]
result = run_python_callable(target=fake_local_agent, input_payload=payload)

print(result.status)
print(result.final_output)
print(result.trace_events)
```

### Compare baseline vs candidate runs

```python
from agent_evalkit.diff.compare import compare_run_results
from agent_evalkit.reports.markdown_report import render_regression_markdown

diff = compare_run_results("runs/baseline", "runs/candidate")
report = render_regression_markdown(diff)

print(report)
```

---

## Example regression report

A typical Markdown report includes:

- summary of baseline and candidate sources
- metric deltas
- changed failure cases
- violation distribution changes
- drift hints

Example drift hints may look like:

- `model_id changed (model-a -> model-b)`
- `network_enabled changed (False -> True)`
- `seed unset in candidate`
- `dependencies hash changed`

---

## CI

The default GitHub Actions workflow is defined in:

```text
.github/workflows/ci.yml
```

It currently runs on:

- `push`
- `pull_request`

And performs:

- dependency installation
- `ruff check .`
- `pytest`
- one deterministic offline example evaluation

When available, CI uploads a small artifact bundle, including:

- test results (`artifacts/pytest-junit.xml`)
- example evaluation output (`artifacts/example_eval.json`)
- run metadata (`artifacts/runs/ci_example_run/run_record.json`)

---

## Design principles

This project intentionally prefers:

- **small and explicit** over broad and abstract
- **deterministic local testing** over fragile remote integration
- **machine-readable outputs** over ad hoc prose
- **regression workflows** over one-off demos

---

## Current limitations

This repository is still intentionally narrow.

Out of scope for the current version:

- web frontend/dashboard
- HTML reporting
- deep MCP-native protocol integration
- large benchmark suites
- network-dependent default tests
- cloud deployment

---

## Roadmap

Near-term improvements may include:

- richer task/result normalization
- stronger report ergonomics
- tighter integration between run records and diff inputs
- configurable CI gate severity
- clearer end-to-end demo commands

---

## Status

This project is currently in an early but functional prototype stage, with:

- deterministic local examples
- core validation and scoring components
- regression comparison support
- CI automation

---

## License

Add a license file before broader open-source distribution.
