from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from . import paths


class BrainError(RuntimeError):
    pass


def extract_json(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise BrainError("model returned empty output")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise BrainError(f"could not parse JSON object from model output: {exc}") from exc

    start = stripped.find("[")
    end = stripped.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise BrainError(f"could not parse JSON array from model output: {exc}") from exc

    raise BrainError("model output did not contain JSON")


def run_cli(script: Path, prompt: str, timeout_s: int = 240) -> str:
    try:
        result = subprocess.run(
            [str(script)],
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(paths.root()),
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BrainError(f"{script.name} timed out after {timeout_s}s") from exc
    if result.returncode != 0:
        raise BrainError(
            f"{script.name} failed with rc={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


def codex_json(prompt: str, timeout_s: int = 240) -> Any:
    output = run_cli(paths.root() / "bin" / "codex-brain.sh", prompt, timeout_s=timeout_s)
    return extract_json(output)


def claude_json(prompt: str, timeout_s: int = 90) -> Any:
    output = run_cli(paths.root() / "bin" / "claude-review.sh", prompt, timeout_s=timeout_s)
    return extract_json(output)
