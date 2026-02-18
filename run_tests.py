"""Helper to run pytest and capture output to a file."""

import subprocess
import sys

venv_python = r".venv\Scripts\python.exe"
args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
cmd = [venv_python, "-m", "pytest"] + args

with open("test_result.txt", "w", encoding="utf-8") as f:
    proc = subprocess.run(
        cmd,
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=600,
    )
    f.write(f"\nRETURN CODE: {proc.returncode}\n")
