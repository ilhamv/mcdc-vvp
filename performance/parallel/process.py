"""Collect parallel runs and generate scaling tables and figures."""

import argparse
import math
import csv
import shutil
from collections import defaultdict
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

from util import case_directory, output_name, performance_tasks, tally_score_paths
from performance.metrics import maximum_relative_variance

parser = argparse.ArgumentParser()
parser.add_argument(
    "maestro_run",
    nargs="?",
    default=None,
    help="Maestro run directory; defaults to the latest maestro_run_*.",
)
args = parser.parse_args()
suite_dir = Path(__file__).resolve().parent


def runtime_value(runtime, name):
    """Read an optional runtime component in seconds."""
    return float(runtime[name][()].item()) if name in runtime else float("nan")


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
    task_config = yaml.safe_load(stream)

tasks = performance_tasks(task_config, launch_config["N_node_max"])
records = []
for task in tasks:
    case_dir = case_directory(suite_dir, task)
    output_file = case_dir / f"{output_name(task)}.h5"
    if not output_file.is_file():
        print(f"Skip incomplete task: {task['name']}")
        continue

    with h5py.File(output_file, "r") as output:
        tally_score_paths(output)
        if "performance" not in output:
            raise ValueError(
                f"Missing performance metrics in {output_file}; rerun with the updated MC/DC."
            )
        performance = output["performance"]
        if int(output["settings/N_particle"][()]) != task["N_particle"]:
            raise ValueError(f"Particle count mismatch in {output_file}.")
        runtime = output["runtime"]
        record = {
            key: task[key]
            for key in (
                "case",
                "N_node",
                "workload_multiplier",
                "total_multiplier",
                "N_particle_base",
                "N_particle",
                "walltime_hours",
            )
        }
        record.update(
            N_batch=int(output["settings/N_batch"][()]),
            N_history=int(performance["N_history"][()]),
            N_rank=int(performance["N_rank"][()]),
            effective_variance=float(performance["effective_variance"][()]),
            runtime_total=float(performance["runtime"][()]),
            runtime_preparation=runtime_value(runtime, "preparation"),
            runtime_simulation=runtime_value(runtime, "simulation"),
            runtime_output=runtime_value(runtime, "output"),
            runtime_bank_management=runtime_value(runtime, "bank_management"),
        )
    if not math.isfinite(record["runtime_total"]) or record["runtime_total"] <= 0:
        raise ValueError(f"Invalid total runtime in {output_file}.")
    if record["N_history"] <= 0 or record["N_rank"] <= 0:
        raise ValueError(f"Invalid history or rank count in {output_file}.")
    if record["N_rank"] != task["N_node"] * launch_config["cpu_cores_per_node"]:
        raise ValueError(
            f"Rank count does not match the full-node launch in {output_file}."
        )
    record["tracking_rate"] = record["N_history"] / record["runtime_total"]
    record["tracking_rate_per_node"] = record["tracking_rate"] / record["N_node"]
    records.append(record)

if not records:
    raise RuntimeError("No completed performance tasks were found.")

results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)
results_dir.mkdir()
shutil.copy2(launch_config_file, results_dir / "launch_config.yaml")
shutil.copy2(task_file, results_dir / "task.yaml")


def save_figure(figure, path):
    """Save and close one performance figure."""
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


groups = defaultdict(list)
for record in records:
    groups[record["case"]].append(record)

for case_name, case_records in groups.items():
    case_records.sort(key=lambda item: (item["N_node"], item["workload_multiplier"]))
    if len({item["N_batch"] for item in case_records}) != 1:
        raise ValueError(
            f"Batch counts must match across matrix points for {case_name}."
        )
    # Use one reference across node counts; prefer fewer nodes on history-count ties.
    reference = max(case_records, key=lambda item: (item["N_history"], -item["N_node"]))
    case_dir = case_directory(suite_dir, reference)
    reference_file = case_dir / f"{output_name(reference)}.h5"
    print(
        f"Reference for {case_name}: {reference_file.name}, N_history={reference['N_history']}"
    )
    for record in case_records:
        variance, count = maximum_relative_variance(
            case_dir / f"{output_name(record)}.h5", reference_file
        )
        record.update(
            reference_N_node=reference["N_node"],
            reference_workload_multiplier=reference["workload_multiplier"],
            reference_N_particle=reference["N_particle"],
            reference_N_history=reference["N_history"],
            N_reference_nonzero_bin=count,
            max_relative_variance=variance,
        )
        if np.isfinite(variance) and variance > 0.0:
            # Convert fractional relative variance to precision in %^-2.
            precision = 1.0e-4 / variance
        else:
            precision = float("nan")
            print(
                f"Omit precision metrics: {case_name}, n={record['N_node']}, "
                f"m={record['workload_multiplier']}, invalid maximum relative variance {variance}"
            )
        record["precision"] = precision
        record["precision_rate"] = precision / record["N_history"]
        record["fom"] = record["tracking_rate"] * record["precision_rate"]

    destination = results_dir / case_name
    destination.mkdir(parents=True)
    with (destination / "records.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(case_records[0]))
        writer.writeheader()
        writer.writerows(case_records)

    by_node = defaultdict(list)
    for record in case_records:
        by_node[record["N_node"]].append(record)
    # Match serial metrics, using a separate curve for each node count.
    for metric, filename, ylabel in (
        ("runtime_total", "runtime", "Runtime [s]"),
        ("tracking_rate", "tracking_rate", "Tracking rate [histories/s]"),
        ("precision", "precision", r"Precision [$\%^{-2}$]"),
        ("precision_rate", "precision_rate", r"Precision rate [$\%^{-2}$/history]"),
        ("fom", "fom", r"FOM [$\%^{-2}$/s]"),
    ):
        figure, axis = plt.subplots(figsize=(7.2, 4.8))
        for N_node, group in sorted(by_node.items()):
            group.sort(key=lambda item: item["N_history"])
            axis.plot(
                [item["N_history"] for item in group],
                [item[metric] for item in group],
                marker="o",
                markerfacecolor="none",
                linewidth=2.0,
                label=f"{N_node} node{'s' if N_node != 1 else ''}",
            )
        axis.set_xscale("log")
        axis.set_yscale("log")
        if not any(
            np.isfinite(item[metric]) and item[metric] > 0.0 for item in case_records
        ):
            axis.set_ylim(0.1, 10.0)
            axis.text(
                0.5,
                0.5,
                "No finite positive values",
                transform=axis.transAxes,
                horizontalalignment="center",
            )
        axis.set(
            xlabel=r"Number of histories, $N$",
            ylabel=ylabel,
            title=f"{case_name}: parallel {filename.replace('_', ' ')}",
        )
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(ncols=2)
        save_figure(figure, destination / f"{filename}.png")

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    for N_node, group in sorted(by_node.items()):
        group.sort(key=lambda item: item["N_history"])
        axis.plot(
            [item["N_history"] for item in group],
            [item["tracking_rate_per_node"] for item in group],
            marker="o",
            label=f"{N_node} node{'s' if N_node != 1 else ''}",
        )
    axis.set_xscale("log", base=2)
    axis.set(xlabel="Source histories", ylabel="Tracking rate per node [histories/s]")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend(ncols=2)
    save_figure(figure, destination / "performance_envelope.png")

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    by_multiplier = defaultdict(list)
    for record in case_records:
        by_multiplier[record["workload_multiplier"]].append(record)
    for multiplier, group in sorted(by_multiplier.items()):
        group.sort(key=lambda item: item["N_node"])
        reference_runtime = group[0]["runtime_total"]
        axis.plot(
            [item["N_node"] for item in group],
            [reference_runtime / item["runtime_total"] for item in group],
            marker="o",
            label=f"m={multiplier}",
        )
    axis.axhline(1.0, color="black", linewidth=1, linestyle="--")
    axis.set_xscale("log", base=2)
    axis.set(xlabel="Nodes", ylabel="Weak-scaling efficiency")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    save_figure(figure, destination / "weak_scaling.png")

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    by_total = defaultdict(list)
    for record in case_records:
        by_total[record["total_multiplier"]].append(record)
    plotted = False
    for total_multiplier, group in sorted(by_total.items()):
        if len(group) < 2:
            continue
        group.sort(key=lambda item: item["N_node"])
        reference = group[0]
        efficiencies = [
            (reference["runtime_total"] * reference["N_node"])
            / (item["runtime_total"] * item["N_node"])
            for item in group
        ]
        axis.plot(
            [item["N_node"] for item in group],
            efficiencies,
            marker="o",
            label=f"total m={total_multiplier}",
        )
        plotted = True
    axis.axhline(1.0, color="black", linewidth=1, linestyle="--")
    axis.set_xscale("log", base=2)
    axis.set(xlabel="Nodes", ylabel="Strong-scaling efficiency")
    axis.grid(True, which="both", alpha=0.3)
    if plotted:
        axis.legend(ncols=2)
    save_figure(figure, destination / "strong_scaling.png")

print(f"Processed {len(records)} tasks into {results_dir}")
