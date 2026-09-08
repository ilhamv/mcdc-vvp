"""Process serial runtimes and generate case performance figures."""

import argparse
import ast
import csv
import shutil
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

from util import MODES, output_name, particle_counts

parser = argparse.ArgumentParser(description="Process the serial-performance suite.")
parser.add_argument(
    "maestro_run",
    nargs="?",
    default=None,
    help="Maestro run directory; defaults to the latest maestro_run_*.",
)
args = parser.parse_args()


def input_batch_count(input_file):
    """Read the single positive N_batch assignment from an input file."""
    tree = ast.parse(input_file.read_text(), filename=str(input_file))
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "N_batch":
                values.append(ast.literal_eval(node.value))
    if len(values) != 1 or isinstance(values[0], bool) or values[0] <= 0:
        raise ValueError(f"Could not determine one positive N_batch from {input_file}.")
    return int(values[0])


def total_runtime(output_file):
    """Return the total runtime stored in one runtime-only output."""
    with h5py.File(output_file, "r") as output:
        runtime = float(output["runtime/total"][0])
    if runtime <= 0.0:
        raise ValueError(f"Invalid total runtime in {output_file}.")
    return runtime


def add_series(axis, histories, python, numba, numba_without_compilation):
    """Add the three requested execution-mode series to an axis."""
    axis.plot(
        histories,
        numba,
        color="blue",
        linestyle="-",
        marker="o",
        markerfacecolor="none",
        label="Numba",
    )
    axis.plot(
        histories,
        python,
        color="red",
        linestyle="--",
        marker="x",
        label="Python",
    )
    axis.plot(
        histories,
        numba_without_compilation,
        color="yellow",
        linestyle=":",
        label="Numba (w/o compilation)",
    )


def save_figure(figure, path):
    """Save and close one performance figure."""
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


suite_dir = Path(__file__).resolve().parent
if args.maestro_run is None:
    maestro_runs = sorted(
        suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
    )
    if not maestro_runs:
        raise FileNotFoundError("No maestro_run_* directory found.")
    maestro_run = maestro_runs[-1]
else:
    maestro_run = Path(args.maestro_run).expanduser()
    if not maestro_run.is_absolute():
        maestro_run = suite_dir / maestro_run

launch_config_file = maestro_run / "launch_config.yaml"
task_file = maestro_run / "task.yaml"
if not launch_config_file.is_file():
    raise FileNotFoundError(f"Launch config not found: {launch_config_file}")
if not task_file.is_file():
    raise FileNotFoundError(f"Task config not found: {task_file}")

with launch_config_file.open("r") as stream:
    launch_config = yaml.safe_load(stream)
with task_file.open("r") as stream:
    tasks = yaml.safe_load(stream)

results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)
results_dir.mkdir()
shutil.copy2(launch_config_file, results_dir / "launch_config.yaml")
shutil.copy2(task_file, results_dir / "task.yaml")


processed_cases = 0
for case_name, task in tasks.items():
    case_dir = suite_dir / "cases" / case_name
    input_file = case_dir / "input.py"
    N_batch = input_batch_count(input_file)
    records = []

    for N_particle in particle_counts(
        task["logN_min"],
        task["logN_max"],
        task["N_task"],
    ):
        N_particle = int(N_particle)
        output_files = {
            mode: case_dir / f"{output_name(mode, N_particle)}.h5" for mode in MODES
        }
        missing = [mode for mode, path in output_files.items() if not path.is_file()]
        if missing:
            print(
                f"Skip incomplete point: {case_name}, N={N_particle}, "
                f"missing {', '.join(missing)}"
            )
            continue

        N_history = N_particle * N_batch
        records.append(
            {
                "N_particle": N_particle,
                "N_batch": N_batch,
                "N_history": N_history,
                "runtime_python": total_runtime(output_files["python"]),
                "runtime_numba": total_runtime(output_files["numba"]),
            }
        )

    if len(records) < 3:
        print(f"Skip incomplete case: {case_name}; fewer than three paired points.")
        continue

    records.sort(key=lambda record: record["N_history"])
    compilation_time = float(
        np.median([record["runtime_numba"] for record in records[:3]])
    )
    for record in records:
        adjusted_runtime = record["runtime_numba"] - compilation_time
        record["runtime_numba_without_compilation"] = (
            adjusted_runtime if adjusted_runtime > 0.0 else float("nan")
        )
        record["tracking_rate_python"] = record["N_history"] / record["runtime_python"]
        record["tracking_rate_numba"] = record["N_history"] / record["runtime_numba"]
        record["tracking_rate_numba_without_compilation"] = (
            record["N_history"] / adjusted_runtime
            if adjusted_runtime > 0.0
            else float("nan")
        )
        record["estimated_compilation_time"] = compilation_time

    destination = results_dir / case_name
    destination.mkdir()
    with (destination / "records.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    histories = [record["N_history"] for record in records]
    runtime_python = [record["runtime_python"] for record in records]
    runtime_numba = [record["runtime_numba"] for record in records]
    runtime_adjusted = [
        record["runtime_numba_without_compilation"] for record in records
    ]

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    add_series(axis, histories, runtime_python, runtime_numba, runtime_adjusted)
    axis.axhline(
        compilation_time,
        color="black",
        linestyle="-",
        label="Compilation time",
    )
    axis.text(
        0.03,
        0.97,
        f"Estimated compilation time: {compilation_time:.2f} s",
        transform=axis.transAxes,
        horizontalalignment="left",
        verticalalignment="top",
        bbox={"facecolor": "white", "edgecolor": "black", "alpha": 0.8},
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set(
        xlabel=r"Number of histories, $N$",
        ylabel=r"Runtime, $T$ [s]",
        title=f"{case_name}: serial runtime",
    )
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    save_figure(figure, destination / "runtime.png")

    tracking_python = [record["tracking_rate_python"] for record in records]
    tracking_numba = [record["tracking_rate_numba"] for record in records]
    tracking_adjusted = [
        record["tracking_rate_numba_without_compilation"] for record in records
    ]
    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    add_series(axis, histories, tracking_python, tracking_numba, tracking_adjusted)
    axis.text(
        0.03,
        0.97,
        f"Estimated compilation time: {compilation_time:.2f} s",
        transform=axis.transAxes,
        horizontalalignment="left",
        verticalalignment="top",
        bbox={"facecolor": "white", "edgecolor": "black", "alpha": 0.8},
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set(
        xlabel=r"Number of histories, $N$",
        ylabel=r"Tracking rate, $T_r$ [histories/s]",
        title=f"{case_name}: serial tracking rate",
    )
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    save_figure(figure, destination / "tracking_rate.png")
    processed_cases += 1

if processed_cases == 0:
    raise RuntimeError("No complete serial-performance cases were found.")

print(f"Processed {processed_cases} cases into {results_dir}")
print(f"Platform: {launch_config['platform']}")
