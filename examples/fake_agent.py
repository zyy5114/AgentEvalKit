"""Deterministic local fake agent for offline adapter testing."""

from __future__ import annotations

import json
from hashlib import sha256
from collections.abc import Mapping
from typing import Any


DEMO_TASK_INPUTS: tuple[dict[str, str], ...] = (
    {"task_id": "offline_echo_1", "input_text": "hello world"},
    {"task_id": "offline_echo_2", "input_text": "2 + 3"},
    {"task_id": "offline_echo_3", "input_text": "agent eval kit"},
    {"task_id": "offline_echo_4", "input_text": "deterministic trace"},
)


def fake_local_agent(input_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic output and deterministic trace metadata.

    Args:
        input_payload: Simple payload containing task fields such as
            ``task_id`` and ``input_text``.

    Returns:
        Mapping with ``final_output`` and ``trace_events`` fields expected by
        ``run_python_callable``.
    """

    task_id = str(input_payload.get("task_id", "task"))
    input_text = _read_input_text(input_payload)
    output_text = f"ECHO::{input_text}"
    payload_fingerprint = _fingerprint_payload(input_payload)

    final_output = {
        "task_id": task_id,
        "answer": output_text,
        "char_count": len(input_text),
        "payload_fingerprint": payload_fingerprint,
    }
    trace_events = [
        {
            "event_type": "step",
            "step_index": 0,
            "message": "parse_input",
            "metadata": {"task_id": task_id, "input_keys": sorted(input_payload.keys())},
        },
        {
            "event_type": "step",
            "step_index": 1,
            "message": "compose_output",
            "metadata": {"char_count": len(input_text)},
        },
        {
            "event_type": "final",
            "step_index": 2,
            "message": "complete",
            "metadata": {"status": "succeeded"},
        },
    ]
    return {
        "final_output": final_output,
        "trace_events": trace_events,
    }


def offline_demo_inputs() -> list[dict[str, str]]:
    """Return 4 deterministic payloads for local offline adapter testing."""
    return [dict(payload) for payload in DEMO_TASK_INPUTS]


def _read_input_text(input_payload: Mapping[str, Any]) -> str:
    """Extract user input text from common task payload keys."""
    for key in ("input_text", "prompt", "question"):
        value = input_payload.get(key)
        if value is not None:
            return str(value)
    return ""


def _fingerprint_payload(input_payload: Mapping[str, Any]) -> str:
    """Create a stable payload fingerprint used in deterministic outputs."""
    stable_json = json.dumps(dict(input_payload), sort_keys=True, separators=(",", ":"))
    return sha256(stable_json.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    for payload in offline_demo_inputs():
        print(json.dumps(fake_local_agent(payload), sort_keys=True))
