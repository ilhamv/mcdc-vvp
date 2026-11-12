"""Build and launch the MC/DC parallel-performance study with Maestro."""

import argparse
import shlex
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
    get_batch_config,
    get_case_walltime,
    get_platform,
    get_task_walltime,
    get_user_config,
    load_selected_tasks,
    maestro_command,
    platform_names,
    platform_resources,
)
from util import (
    NODE_COUNTS,
    case_directory,
    task_output_complete,
    performance_tasks,
)

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC parallel-performance suite."
)
parser.add_argument(
    "--platform", choices=platform_names(include_local=False), default="dane"
)
parser.add_argument(
    "--N_node_max",
    "--N_node",
    type=int,
    choices=NODE_COUNTS,
    default=None,
    help="Largest power-of-two node count to include.",
)
parser.add_argument(
    "--dry_run",
    action="store_true",
    help="Write the platform-specific study file without submitting it.",
)
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Override every matrix job walltime uniformly, in hours.",
)
parser.add_argument("--platforms", nargs="+", help="Override task platform lists.")
args = parser.parse_args()


# ======================================================================================
# Paths and platform settings
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
run_case = suite_dir / "run_case.py"
study_file = suite_dir / f"study_{args.platform}.yaml"
task_config = load_selected_tasks(
    suite_dir, args.platform, args.platforms, args.N_node_max
)
if not task_config:
    print(f"No tasks configured for {args.platform}.")
    raise SystemExit(0)

platform = get_platform(args.platform)
user = get_user_config(args.platform)
batch = get_batch_config(platform, user, dry_run=args.dry_run)
mcdc_python = user["mcdc_python"]
resources = platform_resources(args.platform)

# ======================================================================================
# Load tasks
# ======================================================================================

args.N_node_max = max(settings["N_node"] for settings in task_config.values())
tasks = performance_tasks(task_config, args.N_node_max, args.platform)
for task in tasks:
    get_task_walltime(task, args.walltime)


# ======================================================================================
# Build Maestro study
# ======================================================================================

# Each case or matrix point becomes one independent Maestro step.
steps = []
skipped_tasks = []
case_walltimes = {}
cpu_cores = platform["cpu_cores_per_node"]

for task in tasks:
    case_dir = case_directory(suite_dir, task)
    input_file = case_dir / "input.py"
    if not input_file.is_file():
        raise FileNotFoundError(f"Performance input not found: {input_file}")
    if task_output_complete(suite_dir, task):
        skipped_tasks.append(task["name"])
        print(f"Skip complete task: {task['name']}")
        continue

    walltime = get_case_walltime(task, platform, args.walltime)
    case_walltimes[task["name"]] = walltime
    command = (
        f"{shlex.quote(mcdc_python)} {shlex.quote(str(run_case))} "
        f"--name {shlex.quote(task['case'])} "
        f"--platform {args.platform} "
        f"--nodes {task['N_node']} "
        f"--multiplier {task['workload_multiplier']} "
        f"--N_particle_base {task['N_particle_base']} "
        '--launcher "$(LAUNCHER)"'
    )
    steps.append(
        {
            "name": task["name"],
            "description": (
                f"{task['case']}: {task['N_node']} nodes, "
                f"workload multiplier {task['workload_multiplier']}"
            ),
            "run": {
                "cmd": command,
                "nodes": task["N_node"],
                "procs": task["N_node"] * resources["ranks_per_node"],
                "walltime": walltime,
                "exclusive": True,
            },
        }
    )
    if resources["target"] == "gpu":
        run = steps[-1]["run"]
        run["gpus"] = 1
        if platform["scheduler"] == "flux":
            # Exclusive allocation reserves whole nodes. A nonexclusive inner
            # launcher preserves Flux's explicit one-GPU-per-rank binding.
            run["exclusive"] = {"allocation": True, "launcher": False}
        elif platform["scheduler"] == "lsf":
            run.update(
                {
                    "rs per node": resources["ranks_per_node"],
                    "tasks per rs": 1,
                    "cpus per rs": 1,
                }
            )

study = {
    "description": {
        "name": f"maestro_run_{args.platform}",
        "description": "MC/DC parallel-performance scaling study",
    },
    "env": {"variables": {}},
    "batch": batch,
    "study": steps,
}

# ======================================================================================
# Write Maestro study
# ======================================================================================

with study_file.open("w") as stream:
    yaml.dump(study, stream, sort_keys=False)

# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print(f"Nodes    : 1 through {args.N_node_max} (powers of two)")
print(f"Target   : {resources['target']}")
print(f"Procs    : {resources['ranks_per_node']} per node")
print(f"GPUs     : {resources['gpus_per_node']} per node")
print(f"Tasks    : {len(steps)}")
print(f"Skipped  : {len(skipped_tasks)}")
print(f"Study    : {study_file}")
print(f"Python   : {mcdc_python}")
print(f"Scheduler: {platform['scheduler']}")
print(f"Account  : {batch['bank']}")
print(f"Queue    : {batch.get('queue')}")
print(f"Reserv.  : {batch.get('reservation')}")
print("Exclusive: True")
print("Walltimes:")
for task_name, walltime in case_walltimes.items():
    print(f"  {task_name}: {walltime}")

if args.dry_run or not steps:
    raise SystemExit(0)

# ======================================================================================
# Launch Maestro
# ======================================================================================

command, env = maestro_command(user, study_file.name)
subprocess.run(command, cwd=suite_dir, check=True, env=env)

# ======================================================================================
# Store launch metadata
# ======================================================================================

# Save the effective configuration alongside the generated Maestro run.
maestro_runs = sorted(
    suite_dir.glob(f"maestro_run_{args.platform}_*"),
    key=lambda path: path.stat().st_mtime,
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

launch_config = {
    "platform": args.platform,
    "scheduler": platform["scheduler"],
    "N_node_max": args.N_node_max,
    "cpu_cores_per_node": cpu_cores,
    **resources,
    "output_layout": 2,
    "walltime": args.walltime,
    "task_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}
latest_run = maestro_runs[-1]
with (latest_run / "launch_config.yaml").open("w") as stream:
    yaml.dump(launch_config, stream, sort_keys=False)
with (latest_run / "task.yaml").open("w") as stream:
    yaml.dump(task_config, stream, sort_keys=False)
