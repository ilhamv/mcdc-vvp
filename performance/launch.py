"""Build and launch the MC/DC performance study with Maestro."""

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from configs.platform_config import PLATFORMS
from configs.util import get_case_walltime
from util import (
    NODE_COUNTS,
    WALLTIME_BASE_HOURS,
    case_directory,
    performance_tasks,
    run_directory,
)

try:
    from configs.user_config import USER_CONFIG
except ImportError:
    USER_CONFIG = {}


parser = argparse.ArgumentParser(description="Launch the MC/DC performance suite.")
parser.add_argument("--platform", choices=["dane"], default="dane")
parser.add_argument(
    "--N_node_max",
    type=int,
    choices=NODE_COUNTS,
    default=64,
    help="Largest power-of-two node count to include.",
)
parser.add_argument(
    "--dry_run",
    action="store_true",
    help="Write study.yaml without submitting it.",
)
args = parser.parse_args()


suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"
platform = PLATFORMS[args.platform]
user_platform_config = USER_CONFIG.get(args.platform, {})

if args.N_node_max > platform["max_nodes"]:
    parser.error(
        f"--N_node_max exceeds the {platform['max_nodes']}-node limit for "
        f"{args.platform}."
    )

mcdc_python = user_platform_config.get("mcdc_python")
if mcdc_python is None:
    mcdc_python = sys.executable
else:
    mcdc_python = str(Path(mcdc_python).expanduser())

account = user_platform_config.get("account")
if account is None and not args.dry_run:
    raise ValueError(
        "Platform 'dane' requires an account. Create configs/user_config.py "
        "from configs/user_config.py.template."
    )
if account is None:
    account = "UNCONFIGURED"

with task_file.open("r") as stream:
    task_config = yaml.safe_load(stream)
tasks = performance_tasks(task_config, args.N_node_max)


def input_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_is_current(task, input_file):
    output_dir = run_directory(suite_dir, task)
    output_file = output_dir / "output.h5"
    metadata_file = output_dir / "task.yaml"
    if not output_file.is_file():
        return False
    if not metadata_file.is_file():
        raise RuntimeError(f"Existing output has no task metadata: {output_file}")
    with metadata_file.open("r") as stream:
        metadata = yaml.safe_load(stream)
    expected = task.copy()
    expected["input_sha256"] = input_digest(input_file)
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise RuntimeError(
            f"Existing output does not match the current configuration: {output_file}. "
            "Run performance/cleanup.py before relaunching."
        )
    return True


steps = []
skipped_tasks = []
case_walltimes = {}
cpu_cores = platform["cpu_cores_per_node"]

for task in tasks:
    input_file = case_directory(suite_dir, task) / "input.py"
    if not input_file.is_file():
        raise FileNotFoundError(f"Performance input not found: {input_file}")
    if output_is_current(task, input_file):
        skipped_tasks.append(task["name"])
        print(f"Skip complete task: {task['name']}")
        continue

    walltime = get_case_walltime(
        {"walltime_factor": task["workload_multiplier"]},
        platform,
        WALLTIME_BASE_HOURS,
    )
    case_walltimes[task["name"]] = walltime
    command = (
        f"{mcdc_python} {run_case} "
        f"--problem {task['problem']} "
        f"--method {task['method']} "
        f"--nodes {task['N_node']} "
        f"--multiplier {task['workload_multiplier']} "
        f"--N_particle_base {task['N_particle_base']} "
        '--launcher "$(LAUNCHER)"'
    )
    steps.append(
        {
            "name": task["name"],
            "description": (
                f"{task['problem']}/{task['method']}: {task['N_node']} nodes, "
                f"workload multiplier {task['workload_multiplier']}"
            ),
            "run": {
                "cmd": command,
                "nodes": task["N_node"],
                "procs": task["N_node"] * cpu_cores,
                "walltime": walltime,
                "exclusive": True,
            },
        }
    )

study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC performance scaling study",
    },
    "env": {"variables": {}},
    "batch": {
        "type": platform["scheduler"],
        "host": platform["host"],
        "bank": account,
    },
    "study": steps,
}
queue = user_platform_config.get("queue")
reservation = user_platform_config.get("reservation")
if queue is not None:
    study["batch"]["queue"] = queue
if reservation is not None:
    study["batch"]["reservation"] = reservation

with study_file.open("w") as stream:
    yaml.dump(study, stream, sort_keys=False)

print(f"Platform : {args.platform}")
print(f"Nodes    : 1 through {args.N_node_max} (powers of two)")
print(f"Procs    : {cpu_cores} per node")
print(f"Tasks    : {len(steps)}")
print(f"Skipped  : {len(skipped_tasks)}")
print(f"Study    : {study_file}")

if args.dry_run or not steps:
    raise SystemExit(0)

maestro_python = user_platform_config.get("maestro_python")
env = os.environ.copy()
if maestro_python is None:
    maestro_command = ["maestro", "run", "study.yaml"]
else:
    maestro_python = Path(maestro_python).expanduser()
    env["PATH"] = f"{maestro_python.parent}:{env['PATH']}"
    maestro_command = [
        str(maestro_python),
        "-m",
        "maestrowf.maestro",
        "run",
        "study.yaml",
    ]
subprocess.run(maestro_command, cwd=suite_dir, check=True, env=env)

maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

launch_config = {
    "platform": args.platform,
    "scheduler": platform["scheduler"],
    "N_node_max": args.N_node_max,
    "cpu_cores_per_node": cpu_cores,
    "walltime_base_hours": WALLTIME_BASE_HOURS,
    "task_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}
latest_run = maestro_runs[-1]
with (latest_run / "launch_config.yaml").open("w") as stream:
    yaml.dump(launch_config, stream, sort_keys=False)
with (latest_run / "task.yaml").open("w") as stream:
    yaml.dump(task_config, stream, sort_keys=False)
