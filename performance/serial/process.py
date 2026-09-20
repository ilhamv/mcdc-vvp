"""Process serial runtime and precision metrics and generate performance figures."""

import argparse
import csv
import shutil
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

from util import output_name, tally_score_paths, task_particle_counts, task_modes

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
        tally_score_paths(output)
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


def maximum_relative_variance(output_file, reference_file):
    """Return the maximum squared standard error relative to fixed reference means."""
    maximum = 0.0
    nonzero_bins = 0
    with h5py.File(output_file, "r") as output, h5py.File(
        reference_file, "r"
    ) as reference:
        paths = tally_score_paths(reference)
        if tally_score_paths(output) != paths:
            raise ValueError(f"Tally scores do not match the reference: {output_file}")
        for tally_name in reference["tallies"]:
            reference_grid = reference[f"tallies/{tally_name}"].get("grid")
            output_grid = output[f"tallies/{tally_name}"].get("grid")
            if (reference_grid is None) != (output_grid is None):
                raise ValueError(
                    f"Tally grids do not match the reference: {output_file}"
                )
            if reference_grid is not None:
                if set(reference_grid) != set(output_grid) or any(
                    not np.array_equal(reference_grid[key][()], output_grid[key][()])
                    for key in reference_grid
                ):
                    raise ValueError(
                        f"Tally grids do not match the reference: {output_file}"
                    )
        for path in paths:
            mean = reference[f"{path}/mean"]
            sdev = output[f"{path}/sdev"]
            if sdev.shape != mean.shape:
                raise ValueError(
                    f"Tally shape does not match the reference: {path} in {output_file}"
                )
            # Read slabs to avoid loading large space-time tallies in full.
            if mean.shape:
                row_size = max(1, int(np.prod(mean.shape[1:])))
                stride = max(1, 1_000_000 // row_size)
                selections = (
                    slice(start, start + stride)
                    for start in range(0, mean.shape[0], stride)
                )
            else:
                selections = [()]
            for selection in selections:
                reference_mean = np.asarray(mean[selection])
                standard_error = np.asarray(sdev[selection])
                if not np.all(np.isfinite(reference_mean)):
                    raise ValueError(
                        f"Nonfinite reference mean: {path} in {reference_file}"
                    )
                mask = reference_mean != 0.0
                count = int(np.count_nonzero(mask))
                if not count:
                    continue
                values = standard_error[mask]
                if not np.all(np.isfinite(values)) or np.any(values < 0.0):
                    raise ValueError(
                        f"Invalid tally standard deviation: {path} in {output_file}"
                    )
                relative_variance = (values / reference_mean[mask]) ** 2
                maximum = max(maximum, float(np.max(relative_variance)))
                nonzero_bins += count
    return (maximum if nonzero_bins else float("nan")), nonzero_bins


def add_series(axis, records, metric):
    """Plot each mode using its own available history counts."""
    for mode, color, linestyle, marker, label in (
        ("numba", "#0072B2", "-", "o", "Numba"),
        ("python", "#D55E00", "--", "x", "Python"),
    ):
        key = f"{metric}_{mode}"
        points = [record for record in records if key in record]
        if not points:
            continue
        axis.plot(
            [record["N_history"] for record in points],
            [record[key] for record in points],
            color=color,
            linestyle=linestyle,
            linewidth=2.0,
            marker=marker,
            markerfacecolor="none",
            label=label,
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

# Validate saved mode configurations before replacing existing results.
for task in tasks.values():
    for mode in task_modes(task):
        task_particle_counts(task, mode)

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
    records_by_particle = {}
    output_files = {}

    for mode in modes:
        for N_particle in task_particle_counts(task, mode):
            N_particle = int(N_particle)
            output_file = case_dir / f"{output_name(mode, N_particle)}.h5"
            if not output_file.is_file():
                print(f"Skip incomplete point: {case_name}, {mode}, N={N_particle}")
                continue
            metrics = performance_metrics(output_file)
            output_files[mode, N_particle] = output_file
            if metrics["N_particle"] != N_particle:
                raise ValueError(f"Particle count mismatch in {output_file}.")
            record = records_by_particle.setdefault(
                N_particle,
                {
                    key: metrics[key]
                    for key in ("N_particle", "N_batch", "N_history", "N_rank")
                },
            )
            # Only overlapping points need cross-mode consistency checks.
            for key in ("N_batch", "N_history", "N_rank"):
                if record[key] != metrics[key]:
                    raise ValueError(
                        f"Mismatched {key} between modes for {case_name}, N={N_particle}."
                    )
            record[f"runtime_{mode}"] = metrics["runtime"]
            record[f"effective_variance_{mode}"] = metrics["effective_variance"]

    records = sorted(
        records_by_particle.values(), key=lambda record: record["N_history"]
    )
    if not records:
        print(f"Skip incomplete case: {case_name}; no complete points.")
        continue

    # Both modes use the same largest-history reference; prefer Numba on ties.
    reference_mode, reference_particle = max(
        output_files,
        key=lambda point: (
            records_by_particle[point[1]]["N_history"],
            point[0] == "numba",
        ),
    )
    reference_file = output_files[reference_mode, reference_particle]
    reference_histories = records_by_particle[reference_particle]["N_history"]
    print(
        f"Reference for {case_name}: {reference_file.name}, N_history={reference_histories}"
    )

    for record in records:
        record["reference_mode"] = reference_mode
        record["reference_N_particle"] = reference_particle
        record["reference_N_history"] = reference_histories
        for mode in modes:
            if f"runtime_{mode}" not in record:
                continue
            record[f"tracking_rate_{mode}"] = (
                record["N_history"] / record[f"runtime_{mode}"]
            )
            variance, count = maximum_relative_variance(
                output_files[mode, record["N_particle"]], reference_file
            )
            record[f"max_relative_variance_{mode}"] = variance
            record["N_reference_nonzero_bin"] = count
            if np.isfinite(variance) and variance > 0.0:
                # Convert fractional relative variance to precision in %^-2.
                precision = 1.0e-4 / variance
            else:
                # Undefined or nonpositive variance cannot give a finite precision.
                precision = float("nan")
                print(
                    f"Omit precision metrics: {case_name}, {mode}, "
                    f"N={record['N_history']}, invalid maximum relative variance {variance}"
                )
            record[f"precision_{mode}"] = precision
            record[f"precision_rate_{mode}"] = precision / record["N_history"]
            # With V in percent squared, FOM = (N / T) * (1 / (V * N)).
            record[f"fom_{mode}"] = (
                record[f"tracking_rate_{mode}"] * record[f"precision_rate_{mode}"]
            )

    destination = results_dir / case_name
    destination.mkdir()
    with (destination / "records.csv").open("w", newline="") as stream:
        fieldnames = list(dict.fromkeys(key for record in records for key in record))
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    for metric, title, ylabel in (
        ("runtime", "runtime", r"Runtime, $T$ [s]"),
        ("tracking_rate", "tracking rate", r"Tracking rate, $T_r$ [histories/s]"),
        ("precision", "precision", r"Precision, $1/V_{\%,\max}$ [$\%^{-2}$]"),
        (
            "precision_rate",
            "precision rate",
            r"Precision rate, $1/(V_{\%,\max}N)$ [$\%^{-2}$ history$^{-1}$]",
        ),
        ("fom", "figure of merit", r"FOM, $1/(TV_{\%,\max})$ [$\%^{-2}$ s$^{-1}$]"),
    ):
        figure, axis = plt.subplots(figsize=(7.2, 4.8))
        add_series(axis, records, metric)
        axis.set_xscale("log")
        axis.set_yscale("log")
        if not any(
            np.isfinite(record.get(f"{metric}_{mode}", np.nan))
            and record[f"{metric}_{mode}"] > 0.0
            for record in records
            for mode in modes
        ):
            # An entirely unavailable metric still gets an explicitly empty figure.
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
            title=f"{case_name}: serial {title}",
        )
        axis.grid(True, which="both", alpha=0.3)
        axis.legend()
        save_figure(figure, destination / f"{metric}.png")
    processed_cases += 1

if processed_cases == 0:
    raise RuntimeError("No complete serial-performance cases were found.")

print(f"Processed {processed_cases} cases into {results_dir}")
print(f"Platform: {launch_config['platform']}")
