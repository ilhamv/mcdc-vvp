"""Build and launch the MC/DC serial-performance study with Maestro."""

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
    get_batch_config,
    get_case_walltime,
    get_platform,
    get_task_walltime,
    get_user_config,
    load_suite_tasks,
    maestro_command,
    platform_names,
)
from util import case_outputs_complete, task_modes

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC serial-performance suite."
)
parser.add_argument("--platform", default="local", choices=platform_names())
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Override every case-mode job walltime uniformly, in hours.",
)
parser.add_argument("--N_node", type=int, default=None)
args = parser.parse_args()


# ======================================================================================
# Paths and platform settings
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
run_case = suite_dir / "run_case.py"
study_file = suite_dir / f"study_{args.platform}.yaml"
tasks = load_suite_tasks(suite_dir, args.platform, args.N_node)
if not tasks:
    print("No tasks configured for this suite.")
    raise SystemExit(0)

platform = get_platform(args.platform)
user = get_user_config(args.platform)
batch = get_batch_config(platform, user)
mcdc_python = user["mcdc_python"]

# ======================================================================================
# Load tasks
# ======================================================================================


if batch:
    for task in tasks.values():
        for mode in task_modes(task):
            get_task_walltime(task[mode], args.walltime)


# ======================================================================================
# Build Maestro study
# ======================================================================================

# Each case and execution mode becomes one independent Maestro step.
steps = []
case_walltimes = {}
skipped_tasks = []
for case_name, task in tasks.items():
    case_dir = suite_dir / "cases" / case_name
    input_file = case_dir / "input.py"
    if not input_file.is_file():
        raise FileNotFoundError(f"Serial-performance input not found: {input_file}")

    for mode in task_modes(task):
        step_name = f"{case_name.replace('-', '_')}_{mode}"
        if case_outputs_complete(case_dir, task, mode, args.platform):
            skipped_tasks.append(step_name)
            print(f"Skip complete case and mode: {case_name}, {mode}")
            continue

        command = (
            f"{mcdc_python} {run_case} --name {case_name} --mode {mode} "
            f"--platform {args.platform}"
        )
        if batch:
            command += ' --launcher "$(LAUNCHER)"'

        run = {"cmd": command}
        if batch:
            walltime = get_case_walltime(task[mode], platform, args.walltime)
            case_walltimes[step_name] = walltime
            run.update(nodes=1, procs=1, walltime=walltime, exclusive=True)

        steps.append(
            {
                "name": step_name,
                "description": f"Run serial-performance case: {case_name}, {mode}",
                "run": run,
            }
        )

if not steps:
    print("All configured cases are complete; nothing to launch.")
    raise SystemExit(0)

study = {
    "description": {
        "name": f"maestro_run_{args.platform}",
        "description": "MC/DC serial-performance suite",
    },
    "env": {"variables": {}},
    "study": steps,
}
if batch:
    study["batch"] = batch

# ======================================================================================
# Write Maestro study
# ======================================================================================

with study_file.open("w") as stream:
    yaml.dump(study, stream, sort_keys=False)

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
latest_run = maestro_runs[-1]

launch_config = {
    "platform": args.platform,
    "scheduler": platform["scheduler"],
    "N_node": 1,
    "N_process": 1,
    "walltime": args.walltime if batch else None,
    "case_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
    "output_layout": 2,
}
with (latest_run / "launch_config.yaml").open("w") as stream:
    yaml.dump(launch_config, stream, sort_keys=False)
with (latest_run / "task.yaml").open("w") as stream:
    yaml.dump(tasks, stream, sort_keys=False)

# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print("Nodes    : 1")
print("Procs    : 1")
print(f"Python   : {mcdc_python}")
print(f"Jobs     : {len(steps)} (one per case and mode)")
print(f"Skipped  : {len(skipped_tasks)}")
print(f"Study    : {study_file}")

if batch:
    print(f"Scheduler: {platform['scheduler']}")
    print(f"Account  : {batch['bank']}")
    print(f"Queue    : {batch.get('queue')}")
    print(f"Reserv.  : {batch.get('reservation')}")
    print("Exclusive: True")
    print("Walltimes:")
    for case_name, walltime in case_walltimes.items():
        print(f"  {case_name}: {walltime}")
