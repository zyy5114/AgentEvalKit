# v0.1 CI Gate Design

## Goal

AgentEvalKit is a lightweight, CI-native regression and behavior-aware evaluation toolkit for black-box agent, skill, and CLI/MCP-style workflows.

For v0.1, the CI gate should answer a narrow question on every change:
- did behavior regress against a known baseline in a deterministic local suite?

The design favors fast feedback, low operational overhead, and clear failure signals over broad benchmarking.

## Why Evaluation Should Run In CI

- Prevent silent regressions before merge by making behavior checks part of the default engineering loop.
- Keep evaluation conditions consistent across contributors and branches.
- Preserve evidence (traces, fingerprints, reports) for debugging and reviewer trust.
- Distinguish likely product regression from likely environment drift using run fingerprint diffs.

CI is the correct default enforcement point because local checks are optional, but merge checks are not.

## Gate Semantics (v0.1)

The v0.1 gate is split into two levels:
- hard fail conditions: block merge
- soft warn conditions: do not block merge, but must be visible in report output

### Fail Conditions

Fail the CI job when any of the following are true:
- candidate evaluation command fails to execute
- task spec loading/validation fails for required CI task set
- output schema validation fails for any required CI task
- behavior rule compliance check fails for any task in the required CI task set
- candidate pass rate drops versus baseline by more than configured tolerance (`pass_rate_delta < 0` by default)
- aggregate score drops versus baseline by more than configured tolerance (`score_delta < 0` by default), if aggregate scoring is enabled for the required CI suite
- required report artifact generation fails

### Warn Conditions

Emit warnings (non-blocking) when any of the following are true:
- runtime fingerprint changed in likely drift fields (for example `model_id`, `dependencies_hash`, `network_enabled`, unset `seed`)
- latency worsened above warning threshold while pass/score remain within gate tolerance
- non-required informational tasks fail while required CI tasks pass
- optional artifacts fail to generate, while required artifacts are present

Warnings should appear in both console summary and Markdown report.

### Practical Defaults

For lightweight v0.1 usage, use simple defaults:
- required CI task set: small deterministic suite only
- pass-rate tolerance: `0` (any regression fails)
- score tolerance: `0` (any regression fails)
- latency threshold: warning only

This keeps semantics easy to explain and predictable to debug.

## Artifacts

CI should upload a compact, debugging-oriented artifact bundle per run.

### Required Uploaded Artifacts

- Markdown regression report (`report.md`)
- machine-readable summary (`summary.json`)
- baseline vs candidate diff (`diff.json`)
- normalized execution traces for required tasks (`traces.jsonl` or per-task JSON)
- run fingerprint (`fingerprint.json`)

### Optional Uploaded Artifacts

- raw adapter stdout/stderr logs
- per-task expanded trace files when verbose mode is enabled

If required artifacts are missing, the gate fails.
If optional artifacts are missing, emit a warning only.

## Directory Layout Convention

Use a simple, local-and-CI friendly convention:

```text
runs/
  <run_id>/
    candidate/
      summary.json
      traces/
      fingerprint.json
    baseline/
      summary.json
      traces/
      fingerprint.json
    diff/
      diff.json
    reports/
      report.md

artifacts/
  <run_id>/
    report.md
    summary.json
    diff.json
    traces/
    fingerprint.json
```

Conventions:
- `run_id` should be unique and sortable (for example timestamp + short commit SHA).
- `runs/` is the full local working output for reproducibility and debugging.
- `artifacts/` is the CI upload-ready subset.
- The same filenames should be used across local and CI to reduce glue logic.

The `artifacts/` directory is a CI-oriented export subset of `runs/`, not a second source of truth.

## Future Extensions (Post-v0.1)

- configurable per-task gate severity (`fail` vs `warn`)
- trend-aware gating (regression over N runs, not only baseline/candidate pair)
- separate gates for quality, latency, and cost
- richer drift classification from fingerprint field deltas
- optional HTML report generation

These are intentionally deferred to keep v0.1 small and reliable.
