"""Helper to run pytest and capture output to a file."""

import subprocess
import sys

venv_python = r".venv\Scripts\python.exe"
args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
cmd = [venv_python, "-m", "pytest"] + args

proc = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=600,
)

with open("test_result.txt", "w", encoding="utf-8") as f:
    f.write(f"RETURN_CODE: {proc.returncode}\n\n")
    f.write(proc.stdout or "")
    if proc.stderr:
        f.write("\n--- STDERR ---\n")
        f.write(proc.stderr)

print(f"Done. RC={proc.returncode}")
