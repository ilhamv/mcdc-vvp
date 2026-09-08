"""Shared definitions for serial-performance tasks."""

from pathlib import Path

import numpy as np

MODES = ("python", "numba")


def particle_counts(logN_min, logN_max, N_task):
    """Return logarithmically spaced particles per batch for a case study."""
    return np.logspace(logN_min, logN_max, N_task, dtype=int)


def output_name(mode, N_particle):
    """Return the case-local output name for one mode and particle count."""
    if mode not in MODES:
        raise ValueError(f"Unsupported execution mode: {mode}")
    return f"output_{mode}_{int(N_particle)}"


def case_outputs_complete(case_dir, counts):
    """Return whether both modes exist at every particle count."""
    case_dir = Path(case_dir)
    return all(
        (case_dir / f"{output_name(mode, count)}.h5").is_file()
        for count in counts
        for mode in MODES
    )
