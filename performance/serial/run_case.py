"""Run one serial-performance case over its particle-count study."""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

from util import MODES, output_name, particle_counts

parser = argparse.ArgumentParser(description="Run one MC/DC serial-performance case.")
parser.add_argument("--name", required=True, help="Serial-performance case name.")
parser.add_argument("--task-file", default="task.yaml")
parser.add_argument(
    "--launcher",
    default="",
    help="Process launch command supplied by Maestro.",
)
args = parser.parse_args()


suite_dir = Path(__file__).resolve().parent
case_dir = suite_dir / "cases" / args.name
task_file = suite_dir / args.task_file

if not case_dir.is_dir():
    raise FileNotFoundError(f"Case directory not found: {case_dir}")

with task_file.open("r") as stream:
    tasks = yaml.safe_load(stream)
if args.name not in tasks:
    raise ValueError(f"Case '{args.name}' is not listed in {task_file}")
task = tasks[args.name]


for N_particle in particle_counts(
    task["logN_min"],
    task["logN_max"],
    task["N_task"],
):
    N_particle = int(N_particle)
    for mode in MODES:
        output = output_name(mode, N_particle)
        output_file = case_dir / f"{output}.h5"
        if output_file.is_file():
            print(f"Skip existing output: {args.name}, {mode}, N={N_particle}")
            continue

        command = [
            *shlex.split(args.launcher),
            sys.executable,
            "input.py",
            f"--mode={mode}",
            f"--N_particle={N_particle}",
            f"--output={output}",
            "--no-progress_bar",
            "--no-tally_output",
        ]

        print("=" * 80)
        print(f"Case                : {args.name}")
        print(f"Mode                : {mode}")
        print(f"Particles per batch : {N_particle}")
        print(f"Command             : {shlex.join(command)}")
        print("=" * 80)
        subprocess.run(command, cwd=case_dir, check=True)
