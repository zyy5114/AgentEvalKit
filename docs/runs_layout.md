# Run Layout (Initial v0.1)

Run persistence currently uses a simple per-run directory layout:

```text
runs/
  <run_id>/
    run_record.json
```

The `run_record.json` file stores metadata only at this stage:
- `run_id`
- `task_hash`
- `fingerprint_stub`
- `artifacts_path`
- `started_at`
- `finished_at`
- `status`

This keeps run metadata explicit and machine-readable while execution orchestration is still out of scope.

## Fingerprint Computation (v0.1)

Run fingerprint generation produces a stable JSON-serializable object with fixed keys.
Missing values are explicit (`null`) rather than omitted.

Current fingerprint fields:
- `schema_version`
- `python_version`
- `os`
- `adapter_type`
- `adapter_version`
- `runner_version`
- `dependencies_hash`
- `seed`
- `network_enabled`
- `task_spec_hash`
- `scorer_config_hash`
- `model_id`

Computation notes:
- `python_version` and `os` come from local runtime introspection unless explicit overrides are provided.
- `runner_version` defaults to the package version.
- `dependencies_hash` is a stable SHA-256 digest over available local dependency metadata files (for example `pyproject.toml`, `requirements.txt`, lock files), including file names and bytes.
- `task_spec_hash` and `scorer_config_hash` are stable SHA-256 hashes of canonical JSON (`sort_keys=True`) when payloads are JSON-serializable.
- If any field cannot be determined, it remains present with `null`.
