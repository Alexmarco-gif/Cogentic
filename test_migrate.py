"""Quick test: downgrade to base then upgrade to head."""
import subprocess, sys

# Step 1: downgrade to base
print("=== DOWNGRADE TO BASE ===")
r = subprocess.run(
    [sys.executable, "-m", "alembic.config", "downgrade", "base"],
    capture_output=True, text=True, timeout=120,
)
print("RC:", r.returncode)
if r.stderr:
    # Only print last 1000 chars of stderr
    print("STDERR:", r.stderr[-1000:])

if r.returncode != 0:
    print("Downgrade failed!")
    sys.exit(1)

# Step 2: upgrade to head
print("\n=== UPGRADE TO HEAD ===")
r = subprocess.run(
    [sys.executable, "-m", "alembic.config", "upgrade", "head"],
    capture_output=True, text=True, timeout=300,
)
print("RC:", r.returncode)
if r.stderr:
    print("STDERR:", r.stderr[-2000:])

if r.returncode != 0:
    print("Upgrade failed!")
    sys.exit(1)

# Step 3: check current
print("\n=== CURRENT ===")
r = subprocess.run(
    [sys.executable, "-m", "alembic.config", "current"],
    capture_output=True, text=True, timeout=30,
)
print("RC:", r.returncode)
if r.stderr:
    print("STDERR:", r.stderr[-500:])

print("\nDONE!")
