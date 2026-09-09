"""Process serial runtimes and generate case performance figures."""

import argparse
import csv
import shutil
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

from util import output_name, particle_counts, task_modes

parser = argparse.ArgumentParser(description="Process the serial-performance suite.")
parser.add_argument(
    "maestro_run",
    nargs="?",
    default=None,
    help="Maestro run directory; defaults to the latest maestro_run_*.",
)
args = parser.parse_args()


def performance_metrics(output_file):
    """Read measured performance and settings from one MC/DC output."""
    with h5py.File(output_file, "r") as output:
        if "performance" not in output:
            raise ValueError(
                f"Missing performance metrics in {output_file}; rerun with the updated MC/DC."
            )
        metrics = {
            "runtime": float(output["performance/runtime"][()]),
            "N_history": int(output["performance/N_history"][()]),
            "N_rank": int(output["performance/N_rank"][()]),
            "effective_variance": float(output["performance/effective_variance"][()]),
            "N_particle": int(output["settings/N_particle"][()]),
            "N_batch": int(output["settings/N_batch"][()]),
        }
    if not np.isfinite(metrics["runtime"]) or metrics["runtime"] <= 0.0:
        raise ValueError(f"Invalid total runtime in {output_file}.")
    if metrics["N_history"] <= 0 or metrics["N_rank"] != 1:
        raise ValueError(
            f"Expected positive histories and one MPI rank in {output_file}."
        )
    return metrics


def add_series(axis, histories, python, numba, numba_without_compilation):
    """Add Numba series and the Python series when enabled."""
    axis.plot(
        histories,
        numba,
        color="blue",
        linestyle="-",
        marker="o",
        markerfacecolor="none",
        label="Numba",
    )
    if python is not None:
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
    modes = task_modes(task)
    case_dir = suite_dir / "cases" / case_name
    records = []

    for N_particle in particle_counts(
        task["logN_min"],
        task["logN_max"],
        task["N_task"],
    ):
        N_particle = int(N_particle)
        output_files = {
            mode: case_dir / f"{output_name(mode, N_particle)}.h5" for mode in modes
        }
        missing = [mode for mode, path in output_files.items() if not path.is_file()]
        if missing:
            print(
                f"Skip incomplete point: {case_name}, N={N_particle}, "
                f"missing {', '.join(missing)}"
            )
            continue

        metrics = {
            mode: performance_metrics(path) for mode, path in output_files.items()
        }
        for mode in modes:
            if metrics[mode]["N_particle"] != N_particle:
                raise ValueError(f"Particle count mismatch in {output_files[mode]}.")
        for key in ("N_batch", "N_history", "N_rank"):
            if any(metrics[mode][key] != metrics["numba"][key] for mode in modes):
                raise ValueError(
                    f"Mismatched {key} between Python and Numba for {case_name}, N={N_particle}."
                )
        record = {
            key: metrics["numba"][key]
            for key in ("N_particle", "N_batch", "N_history", "N_rank")
        }
        for mode in modes:
            record[f"runtime_{mode}"] = metrics[mode]["runtime"]
            record[f"effective_variance_{mode}"] = metrics[mode]["effective_variance"]
        records.append(record)

    if len(records) < 3:
        print(f"Skip incomplete case: {case_name}; fewer than three complete points.")
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
        for mode in modes:
            record[f"tracking_rate_{mode}"] = (
                record["N_history"] / record[f"runtime_{mode}"]
            )
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
    runtime_python = (
        [record["runtime_python"] for record in records] if "python" in modes else None
    )
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

    tracking_python = (
        [record["tracking_rate_python"] for record in records]
        if "python" in modes
        else None
    )
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
