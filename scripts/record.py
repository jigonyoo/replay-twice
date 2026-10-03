"""Save exact command, merged output and exit status, without removing files."""
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
name, *command = sys.argv[1:]
if command and command[0] == "--":
    command.pop(0)
target = root / "evidence" / f"{name}.txt"
if target.exists():
    raise SystemExit(f"evidence already exists: {target}; choose a new name")
result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
output = f"$ {shlex.join(command)}\n{result.stdout}\n[exit_code={result.returncode}]\n"
target.write_text(output, encoding="utf-8")
print(output, end="")
raise SystemExit(result.returncode)
