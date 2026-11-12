"""Build and launch the SINBAD validation study with Maestro."""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

# ======================================================================================
# Bootstrap VVP imports
# ======================================================================================

REPO_DIR = Path(__file__).resolve().parents[2]

if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


# ======================================================================================
# Load shared VVP configs
# ======================================================================================

from configs.util import (
    allocation_metadata,
    get_batch_config,
    get_case_walltime,
    get_platform,
    get_task_walltime,
    get_user_config,
    maestro_command,
    platform_names,
    select_tasks,
)
from util import case_directory, load_tasks, output_file

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="Launch the MC/DC VVP SINBAD suite.")
parser.add_argument("--platform", default="local", choices=platform_names())
parser.add_argument("--N_node", type=int, default=None, help="Set the number of nodes.")
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Override every case job walltime uniformly, in hours.",
)
parser.add_argument("--platforms", nargs="+", help="Override task platform lists.")
args = parser.parse_args()

# ======================================================================================
# Paths and tasks
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"

config, _ = load_tasks(task_file)
task_config = select_tasks(
    config, suite_dir, args.platform, args.platforms, args.N_node
)
if not task_config:
    print(f"No tasks configured for {args.platform}.")
    raise SystemExit(0)
tasks = [
    (benchmark, case, task)
    for benchmark, cases in task_config.items()
    for case, task in cases.items()
]


for benchmark, case, task in tasks:
    get_task_walltime(task, args.walltime)


# ======================================================================================
# Platform settings
# ======================================================================================

platform = get_platform(args.platform)
user = get_user_config(args.platform)
batch = get_batch_config(platform, user)
mcdc_python = user["mcdc_python"]
cpu_cores = platform["cpu_cores_per_node"]


# ======================================================================================
# Build Maestro study
# ======================================================================================

steps = []
case_walltimes = {}
case_nodes = {}
skipped_cases = []

for benchmark, case, task in tasks:
    name = f"{benchmark}/{case}"
    case_dir = case_directory(suite_dir, benchmark, case)
    nodes = task["N_node"]
    input_file = case_dir / "input.py"
    N_particle = task["N_particle"]

    if not input_file.is_file():
        raise FileNotFoundError(f"Case input not found: {input_file}")

    if output_file(case_dir, N_particle).is_file():
        skipped_cases.append(name)
        print(f"Skip complete case: {name}")
        continue

    safe_name = name.replace("-", "_").replace("/", "__")
    command = f"{mcdc_python} {run_case} --benchmark {benchmark} --case {case}"
    if batch:
        command += ' --launcher "$(LAUNCHER)"'

    case_nodes[name] = nodes
    run = {"cmd": command}
    if batch:
        walltime = get_case_walltime(task, platform, args.walltime)
        case_walltimes[name] = walltime
        run.update(
            {
                "nodes": nodes,
                "walltime": walltime,
                "procs": nodes * cpu_cores,
                "exclusive": True,
            }
        )

    steps.append(
        {
            "name": safe_name,
            "description": f"Run SINBAD case: {name}",
            "run": run,
        }
    )

if not steps:
    print("All configured cases are complete; nothing to launch.")
    raise SystemExit(0)

study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC validation - SINBAD suite",
    },
    "env": {"variables": {}},
    "study": steps,
}

if batch:
    study["batch"] = batch


# ======================================================================================
# Write and launch the study
# ======================================================================================

with study_file.open("w") as file:
    yaml.dump(study, file, sort_keys=False)

command, env = maestro_command(user, study_file.name)
subprocess.run(command, cwd=suite_dir, check=True, env=env)


# ======================================================================================
# Store launch metadata
# ======================================================================================

maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

latest_run = maestro_runs[-1]
launch_config = {
    "platform": args.platform,
    "scheduler": platform["scheduler"],
    **allocation_metadata(case_nodes, cpu_cores),
    "walltime": args.walltime,
    "case_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}

with (latest_run / "launch_config.yaml").open("w") as file:
    yaml.dump(launch_config, file, sort_keys=False)
with (latest_run / "task.yaml").open("w") as file:
    yaml.dump(task_config, file, sort_keys=False)


# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print(f"Nodes    : {launch_config['N_node'] or case_nodes}")
print(f"Python   : {mcdc_python}")
print(f"Study    : {study_file}")
if batch:
    print(f"Scheduler: {batch['type']}")
    print(f"Account  : {batch['bank']}")
    print(f"Queue    : {batch.get('queue')}")
    print(f"Reserv.  : {batch.get('reservation')}")
    print("Walltimes:")
    for name, walltime in case_walltimes.items():
        print(f"  {name}: {walltime}")

print(f"Cases    : {len(steps)}")
print(f"Skipped  : {len(skipped_cases)}")
