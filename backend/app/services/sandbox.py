"""Safe subprocess code execution sandbox for verifying solutions."""
import asyncio
import subprocess
import tempfile
import sys
import re
from pathlib import Path
from typing import Dict, Any


def _run_subprocess(temp_path: str, timeout_seconds: int) -> Dict[str, Any]:
    """Synchronous subprocess execution safe on Windows Selector/Proactor event loops."""
    try:
        proc = subprocess.run(
            [sys.executable, temp_path],
            input="10 20 30 40 50\n",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tempfile.gettempdir()
        )
        passed = (proc.returncode == 0)
        out_str = proc.stdout.strip()
        err_str = proc.stderr.strip()

        return {
            "output": out_str if out_str else ("Code executed successfully." if passed else err_str),
            "error": err_str if not passed else None,
            "passed": passed,
            "exit_code": proc.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "output": "",
            "error": f"Execution timed out after {timeout_seconds} seconds.",
            "passed": False,
            "exit_code": -1
        }
    except Exception as e:
        return {
            "output": "",
            "error": f"Execution error: {str(e)}",
            "passed": False,
            "exit_code": -1
        }


async def execute_python_code(code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    Executes Python code in an isolated subprocess with a strict timeout.
    Returns:
        {
            "output": str,
            "error": str | None,
            "passed": bool,
            "exit_code": int
        }
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir(), encoding="utf-8"
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        return await asyncio.to_thread(_run_subprocess, temp_path, timeout_seconds)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def extract_python_code(markdown_text: str) -> str | None:
    """Extract the first python code block from markdown string."""
    matches = re.findall(r"```(?:python|py)\s*\n(.*?)\s*```", markdown_text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()
    return None
