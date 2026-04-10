# AGENTS.md

## Project
Build **AgentEvalKit**: a lightweight, CI-native regression and behavior-aware evaluation toolkit for black-box agent, skill, and CLI/MCP-style workflows.

The project focuses on:
- declarative task specs
- output validation
- behavior-aware scoring
- run fingerprinting
- baseline vs candidate regression comparison
- Markdown reporting
- GitHub Actions integration

## Product intent
AgentEvalKit is **not** another agent application.
It is an engineering tool for evaluating and regression-testing agent-style workflows.

The core questions this repository should help answer are:
1. Did the new version get better or worse?
2. Did the runtime environment change?
3. Which behavioral rules were violated?
4. Is the change likely caused by system regression or environment drift?

## v0.1 scope
The following are in scope for v0.1:
- YAML task spec loading
- Python callable adapter
- CLI adapter
- JSON Schema-based output validation
- behavior compliance scoring
- normalized execution traces
- run fingerprint generation
- baseline vs candidate diff
- Markdown report generation
- GitHub Actions CI
- local example tasks and deterministic fake agents

## Out of scope for v0.1
The following are explicitly out of scope unless the user asks to change scope:
- HTML report
- web frontend or dashboard
- deep MCP-native protocol integration
- more than 2 adapters
- more than 12 example tasks
- live network-dependent tests by default
- heavy benchmark datasets
- cloud deployment
- large refactors unrelated to the requested task

## Technical stack
Use the following defaults unless there is a clear reason not to:
- Python 3.11
- Typer for CLI
- Pydantic for typed schemas/models
- pytest for tests
- jsonschema for JSON Schema validation
- PyYAML with safe loading
- ruff for linting
- pre-commit for local checks

Keep dependencies minimal.
Prefer standard library solutions when practical.

## Architecture principles
1. Keep modules small, typed, and explicit.
2. Prefer simple data structures over framework-heavy abstractions.
3. Keep public interfaces stable and easy to understand.
4. Design for deterministic local testing first.
5. Avoid premature generalization.
6. Black-box compatibility matters more than deep framework coupling.
7. Behavior rules must be executable, not just descriptive prose.
8. Reports should be machine-readable first, human-readable second.

## Repository mental model
The repository should roughly follow this structure:

- `agent_evalkit/specs/` for task spec loading and validation
- `agent_evalkit/runners/` for run execution and run record persistence
- `agent_evalkit/adapters/` for CLI and Python adapters
- `agent_evalkit/scorers/` for output and behavior scoring
- `agent_evalkit/traces/` for trace collection and validation
- `agent_evalkit/fingerprint/` for environment snapshotting and normalized fingerprints
- `agent_evalkit/diff/` for baseline vs candidate comparison and drift hints
- `agent_evalkit/reports/` for Markdown and JSON reporting
- `schemas/` for JSON Schemas
- `examples/` for runnable demo tasks and fake agents
- `tests/` for unit and integration tests
- `docs/` for design notes

Do not reorganize the repository unless the task specifically requires it.

## Task spec expectations
Task specs are declarative and YAML-based.

A minimal task spec should support fields like:
- `task_id`
- `description`
- `input`
- `adapter`
- `output_schema`
- `behavior_rules`
- `scorers`

Behavior rules should be executable and structured.
Examples of acceptable behavior rule fields:
- `forbid_tools`
- `require_tools_any_of`
- `max_steps`
- `max_tool_calls`
- `trace_required`
- `timeout_sec`

Do not convert behavior rules into vague natural-language-only checks.

## Trace expectations
Execution traces should be normalized and explicit.
They should contain enough information for behavior scoring and debugging.

Traces should make it possible to inspect:
- tool calls
- step count
- timeouts
- return codes or execution outcomes
- major run events
- final status

Trace validation failures should be visible and machine-readable.

## Fingerprint expectations
Each run should produce a normalized run fingerprint to help distinguish likely regression from environment drift.

Capture as many of the following as are available:
- `model_id`
- `adapter_type`
- `adapter_version`
- `runner_version`
- `python_version`
- `os`
- `dependencies_hash`
- `network_enabled`
- `seed`
- `task_spec_hash`
- `scorer_config_hash`

Missing values should be explicit rather than silently omitted.

## Diff and reporting expectations
Baseline vs candidate diff should be concise, practical, and debugging-oriented.

A useful diff should include:
- pass/success rate delta
- score delta
- latency delta when available
- changed failure cases
- changes in violations distribution
- drift hints derived from fingerprint differences

Examples of drift hints:
- model changed
- network enabled changed
- seed unset
- dependency hash changed

Prefer short, high-signal Markdown reports over verbose prose.

## Testing rules
Every new parser, scorer, adapter, trace validator, diff utility, or fingerprint function should have tests.

Testing priorities:
1. deterministic unit tests
2. fixture-based integration tests
3. lightweight end-to-end local demo tests

Use local deterministic fixtures whenever possible.
Do not add default tests that depend on external services or live network access.

Use `tmp_path` for filesystem isolation in tests that write files.

## Coding rules
- Use type hints on public functions and core data models.
- Write clear docstrings on public modules/classes/functions.
- Keep functions focused.
- Prefer explicit names over clever names.
- Prefer straightforward control flow.
- Handle errors clearly and predictably.
- Do not introduce broad abstractions without evidence they are needed.
- Do not redesign unrelated modules while solving a scoped task.
- Keep diffs small and task-focused.

## CLI expectations
The CLI should stay simple.
Commands should be easy to discover and easy to run locally.

Target style:
- `aek run ...`
- `aek diff ...`
- `aek validate ...`

CLI help text should be short and practical.

## Documentation rules
When public behavior changes, update relevant docs.
At minimum, keep these in sync:
- `README.md`
- example task specs
- quickstart commands
- any changed CLI usage

Do not claim unsupported features.
Do not oversell roadmap items as completed functionality.

## CI expectations
CI should be lightweight and reliable for v0.1.

The default CI workflow should:
- install dependencies
- run lint/tests
- run a tiny deterministic example suite when practical
- upload useful artifacts when helpful

Keep permissions minimal and explicit.
Do not add unnecessary matrix builds or deployment steps in v0.1.

## Performance and scope discipline
This project should feel **small and sharp**, not broad and unfinished.

Prefer:
- fewer features, better finished
- fewer adapters, better tested
- fewer tasks, better documented
- fewer metrics, better explained

When choosing between breadth and polish, choose polish.

## Decision rules for changes
When implementing a task, prioritize in this order:
1. correctness
2. deterministic behavior
3. testability
4. readability
5. low dependency weight
6. extensibility

When a proposed change conflicts with v0.1 scope, do not implement it unless explicitly requested.

## How to respond when working on a task
When given a coding task:
1. Read this file first.
2. Stay within the requested scope.
3. Modify only relevant files.
4. Add or update tests.
5. Run the smallest useful validation commands.
6. Summarize changed files and validation steps.
7. Mention any unresolved issues briefly and clearly.

## Validation checklist
Before considering a task done, verify as many of these as apply:
- code is typed
- tests for changed logic exist
- changed tests pass
- examples still make sense
- public docs are updated when behavior changed
- no unnecessary dependency was added
- no unrelated module was redesigned

## Anti-patterns to avoid
Avoid these unless explicitly requested:
- broad framework rewrites
- speculative abstractions
- hidden magic behavior
- silent fallback logic that obscures failures
- network-dependent default tests
- adding UI/frontend work
- adding support for many adapters at once
- turning a scoped task into a repo-wide cleanup

## Preferred project summary
When describing the project in docs or code comments, prefer wording close to:

"AgentEvalKit is a lightweight, CI-native regression and behavior-aware evaluation toolkit for black-box agent, skill, and CLI/MCP-style workflows."

Do not describe it as a general-purpose agent platform or a full benchmark ecosystem.

## Current success bar for v0.1
A good v0.1 should make it easy to:
- define a small set of tasks in YAML
- run them through CLI or Python adapters
- validate final outputs with JSON Schema
- validate behavior with executable rules
- collect traces and fingerprints
- compare baseline vs candidate runs
- generate a concise Markdown regression report
- run core checks in GitHub Actions
