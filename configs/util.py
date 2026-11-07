"""Shared helpers for VVP configuration and launch processing."""

import math
from pathlib import Path


def case_outputs_complete(case_dir, sample_counts):
    """Return whether every expected sample output exists for a case."""
    case_dir = Path(case_dir)
    return all(
        (case_dir / f"output_{int(count)}.h5").is_file() for count in sample_counts
    )


def get_task_walltime(task, walltime_override=None):
    """Validate required task hours, then apply an optional uniform override."""
    if "walltime_factor" in task:
        raise ValueError("Replace walltime_factor with required walltime in hours.")
    if "walltime" not in task:
        raise ValueError("Each task must define walltime in hours.")

    def validate(value, label):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0.0
        ):
            raise ValueError(f"{label} must be a finite number greater than zero.")
        return value

    hours = validate(task["walltime"], "Task walltime")
    if walltime_override is not None:
        hours = validate(walltime_override, "Launch walltime")
    return hours


def get_case_walltime(task, platform, walltime_override=None):
    """Format task or override hours, rounded and capped for the scheduler."""
    hours = get_task_walltime(task, walltime_override)

    # Round up to the scheduler resolution, then enforce the platform limit.
    resolution = platform["walltime_resolution_seconds"]
    max_seconds = (
        math.floor(platform["max_walltime_hours"] * 3600.0 / resolution) * resolution
    )
    walltime_seconds = math.ceil(hours * 3600.0 / resolution) * resolution
    walltime_seconds = min(walltime_seconds, max_seconds)

    # Convert seconds into the scheduler-specific walltime syntax.
    hours, remainder = divmod(walltime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return platform["walltime_format"].format(
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )
