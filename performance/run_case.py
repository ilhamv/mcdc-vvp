"""Run one point in a performance-case scaling matrix."""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from util import case_directory, output_name, performance_task

parser = argparse.ArgumentParser()
parser.add_argument("--problem", required=True)
parser.add_argument("--method", required=True)
parser.add_argument("--nodes", type=int, required=True)
parser.add_argument("--multiplier", type=int, required=True)
parser.add_argument("--N_particle_base", type=int, required=True)
parser.add_argument("--launcher", default="")
args = parser.parse_args()

suite_dir = Path(__file__).resolve().parent
task = performance_task(
    args.problem,
    args.method,
    args.N_particle_base,
    args.nodes,
    args.multiplier,
)
case_dir = case_directory(suite_dir, task)
input_file = case_dir / "input.py"
output = output_name(task)
output_file = case_dir / f"{output}.h5"

if not input_file.is_file():
    raise FileNotFoundError(input_file)

if output_file.is_file():
    print(f"Skip complete task: {task['name']}")
    raise SystemExit(0)

command = [
    *shlex.split(args.launcher),
    sys.executable,
    "input.py",
    "--mode=numba",
    f"--N_particle={task['N_particle']}",
    f"--output={output}",
    "--no-progress_bar",
    "--caching",
    "--runtime_output",
]

print("=" * 80)
print(f"Task                : {task['name']}")
print(f"Nodes               : {task['N_node']}")
print(f"Workload multiplier : {task['workload_multiplier']}")
print(f"Particles per batch : {task['N_particle']}")
print(f"Command             : {shlex.join(command)}")
print("=" * 80)
subprocess.run(command, cwd=case_dir, check=True)
