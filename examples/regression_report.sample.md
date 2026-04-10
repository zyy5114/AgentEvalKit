# AgentEvalKit Regression Report

## Summary
- Baseline source: `runs/base`
- Candidate source: `runs/candidate`
- Tasks: baseline=3, candidate=4, shared=3

## Metric Deltas
| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Success rate | 66.7% | 50.0% | -16.7 pp |
| Score | 0.667 | 0.500 | -0.167 |
| Latency (sec) | 2.000 | 1.750 | -0.250 |

## Changed Failure Cases
- `pass -> fail`: `task_c`
- `fail -> pass`: `task_b`
- `violation type changes`:
  - `task_c`: none -> `forbidden_tool_used`

## Violation Distribution
| Violation type | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| `forbidden_tool_used` | 0 | 1 | +1 |
| `missing_trace` | 1 | 0 | -1 |

## Drift Hints
- model_id changed (model-a -> model-b)
- network_enabled changed (False -> True)
- seed unset in candidate
- dependencies hash changed
