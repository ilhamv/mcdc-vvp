"""Shared definitions for serial-performance tasks."""

from pathlib import Path

import h5py
import numpy as np

MODES = ("numba", "python")


def task_modes(task):
    """Return the execution modes enabled for a serial-performance case."""
    modes = tuple(mode for mode in MODES if mode in task)
    if not modes:
        raise ValueError("Each case must define a numba and/or python task block.")
    for mode in modes:
        if not isinstance(task[mode], dict):
            raise ValueError(f"Case {mode} settings must be a mapping.")
    return modes


def particle_counts(logN_min, logN_max, N_task):
    """Return logarithmically spaced particles per batch for a case study."""
    return np.logspace(logN_min, logN_max, N_task, dtype=int)


def task_particle_counts(task, mode):
    """Return the particle counts configured for one execution mode."""
    if mode not in task_modes(task):
        raise ValueError(f"Mode '{mode}' is not enabled for this case.")
    settings = task[mode]
    return particle_counts(
        settings["logN_min"], settings["logN_max"], settings["N_task"]
    )


def output_name(mode, N_particle):
    """Return the case-local output name for one mode and particle count."""
    if mode not in MODES:
        raise ValueError(f"Unsupported execution mode: {mode}")
    return f"output_{mode}_{int(N_particle)}"


def tally_score_paths(output):
    """Return tally-score groups with matching mean and standard-deviation datasets."""
    paths = []
    if "tallies" in output:
        for tally_name, tally in output["tallies"].items():
            for score_name, score in tally.items():
                if not isinstance(score, h5py.Group):
                    continue
                if "mean" not in score and "sdev" not in score:
                    continue
                if (
                    "mean" not in score
                    or "sdev" not in score
                    or score["mean"].shape != score["sdev"].shape
                ):
                    raise ValueError(
                        f"Incomplete tally score: {score.name} in {output.filename}"
                    )
                paths.append(f"tallies/{tally_name}/{score_name}")
    if not paths:
        raise ValueError(
            f"Missing full tally results in {output.filename}; move the old output "
            "aside and rerun without --no-tally_output."
        )
    return sorted(paths)


def output_complete(output_file):
    """Check for an existing output and reject files lacking required tally results."""
    if not output_file.is_file():
        return False
    with h5py.File(output_file, "r") as output:
        tally_score_paths(output)
    return True


def case_outputs_complete(case_dir, task, mode):
    """Return whether all configured outputs exist for one case and mode."""
    case_dir = Path(case_dir)
    return all(
        output_complete(case_dir / f"{output_name(mode, count)}.h5")
        for count in task_particle_counts(task, mode)
    )
