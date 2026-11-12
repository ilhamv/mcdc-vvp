"""Build and launch the analytical k-eigenvalue verification study."""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

# ======================================================================================
# Bootstrap VVP imports
# ======================================================================================

REPO_DIR = Path(__file__).resolve().parents[4]

# Support launching this suite directly without installing MC/DC-VVP.
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
    load_selected_tasks,
    maestro_command,
    platform_names,
)
from verification.util import case_outputs_complete

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC VVP analytical multigroup k-eigenvalue suite."
)
parser.add_argument("--platform", default="local", choices=platform_names())
parser.add_argument(
    "--N_node",
    type=int,
    default=None,
    help="Set the number of compute nodes.",
)
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Override every case job walltime uniformly, in hours.",
)
parser.add_argument("--platforms", nargs="+", help="Override task platform lists.")
args = parser.parse_args()

# ======================================================================================
# Paths
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"


# ======================================================================================
# Tasks and platform settings
# ======================================================================================

tasks = load_selected_tasks(suite_dir, args.platform, args.platforms, args.N_node)
if not tasks:
    print(f"No tasks configured for {args.platform}.")
    raise SystemExit(0)

platform = get_platform(args.platform)
user = get_user_config(args.platform)
batch = get_batch_config(platform, user)
mcdc_python = user["mcdc_python"]
cpu_cores = platform["cpu_cores_per_node"]


for task in tasks.values():
    get_task_walltime(task, args.walltime)


# ======================================================================================
# Build Maestro study
# ======================================================================================

# Convert each configured case into one independent Maestro step.
steps = []
case_walltimes = {}
case_nodes = {}
skipped_cases = []

for case_name, task in tasks.items():
    nodes = task["N_node"]
    case_dir = suite_dir / "cases" / case_name
    counts = np.rint(
        np.geomspace(
            task["N_active_min"],
            task["N_active_max"],
            task["N_task"],
        )
    ).astype(int)

    # Do not allocate a Maestro step when every sampling level is already present.
    if case_outputs_complete(case_dir, counts):
        skipped_cases.append(case_name)
        print(f"Skip complete case: {case_name}")
        continue

    # Normalize case names into stable Maestro step identifiers.
    safe_case_name = case_name.replace("-", "_")
    command = f"{mcdc_python} {run_case} --name {case_name}"

    # Maestro replaces LAUNCHER with the scheduler-specific process launcher.
    if batch:
        command += ' --launcher "$(LAUNCHER)"'

    case_nodes[case_name] = nodes
    run = {"cmd": command}

    # Scheduled studies require explicit resources; local studies run directly.
    if batch:
        run["nodes"] = nodes
        walltime = get_case_walltime(task, platform, args.walltime)
        run["walltime"] = walltime
        case_walltimes[case_name] = walltime
        run["procs"] = nodes * cpu_cores
        run["exclusive"] = True

    steps.append(
        {
            "name": safe_case_name,
            "description": f"Run case: {case_name}",
            "run": run,
        }
    )

if not steps:
    print("All configured cases are complete; nothing to launch.")
    raise SystemExit(0)

# Assemble the complete Maestro study from the generated case steps.
study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC verification - analytical multigroup - k-eigenvalue suite",
    },
    "env": {"variables": {}},
    "study": steps,
}

if batch:
    study["batch"] = batch


# ======================================================================================
# Write Maestro study
# ======================================================================================

with study_file.open("w") as f:
    yaml.dump(study, f, sort_keys=False)


# ======================================================================================
# Launch Maestro
# ======================================================================================

command, env = maestro_command(user, study_file.name)
subprocess.run(command, cwd=suite_dir, check=True, env=env)


# ======================================================================================
# Store launch metadata
# ======================================================================================

# Maestro creates timestamped run directories, so capture the newly generated launch.
maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"),
    key=lambda path: path.stat().st_mtime,
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

# Snapshot the effective launch and task configuration with the generated run.
with (latest_run / "launch_config.yaml").open("w") as f:
    yaml.dump(launch_config, f, sort_keys=False)

with (latest_run / "task.yaml").open("w") as f:
    yaml.dump(tasks, f, sort_keys=False)


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
    for case_name, walltime in case_walltimes.items():
        print(f"  {case_name}: {walltime}")


print(f"Cases    : {len(steps)}")
print(f"Skipped  : {len(skipped_cases)}")
