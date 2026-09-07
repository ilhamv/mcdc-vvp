"""Run one point in a performance-case scaling matrix."""

import argparse
import hashlib
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from util import case_directory, performance_task, run_directory

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
input_file = case_directory(suite_dir, task) / "input.py"
output_dir = run_directory(suite_dir, task)
output_dir.mkdir(parents=True, exist_ok=True)
output_base = output_dir / "output"
output_file = output_dir / "output.h5"
metadata_file = output_dir / "task.yaml"

if not input_file.is_file():
    raise FileNotFoundError(input_file)

metadata = task.copy()
metadata["input_sha256"] = hashlib.sha256(input_file.read_bytes()).hexdigest()
if output_file.is_file():
    if not metadata_file.is_file():
        raise RuntimeError(f"Existing output has no task metadata: {output_file}")
    with metadata_file.open("r") as stream:
        recorded = yaml.safe_load(stream)
    if any(recorded.get(key) != value for key, value in metadata.items()):
        raise RuntimeError(f"Existing output is stale: {output_file}")
    print(f"Skip complete task: {task['name']}")
    raise SystemExit(0)

command = [
    *shlex.split(args.launcher),
    sys.executable,
    str(input_file),
    "--mode=numba",
    f"--N_particle={task['N_particle']}",
    f"--output={output_base}",
    "--no-progress_bar",
    "--caching",
    "--runtime_output",
]
metadata["command"] = shlex.join(command)
with metadata_file.open("w") as stream:
    yaml.dump(metadata, stream, sort_keys=False)

print("=" * 80)
print(f"Task                : {task['name']}")
print(f"Nodes               : {task['N_node']}")
print(f"Workload multiplier : {task['workload_multiplier']}")
print(f"Particles per batch : {task['N_particle']}")
print(f"Command             : {shlex.join(command)}")
print("=" * 80)
subprocess.run(command, cwd=output_dir, check=True)
