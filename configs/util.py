"""Shared helpers for VVP configuration and launch processing."""

import math
from pathlib import Path

from configs.platform_config import PLATFORMS


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


def platform_list(value):
    if not isinstance(value, list) or any(
        not isinstance(name, str) or name not in {"local", *PLATFORMS} for name in value
    ):
        raise ValueError(f"Invalid platforms list: {value!r}")
    return value


def select_tasks(config, suite_dir, platform, platforms=None, N_node=None):
    """Return the selected task mapping, with effective resources for the run."""
    override = [] if platforms is None else platform_list(platforms)
    default_nodes = 128 if suite_dir.name == "parallel" else 1
    nested = suite_dir.name in {"sinbad", "serial"}
    selected = {}
    for case, settings in config.items():
        for mode, task in (settings.items() if nested else [(None, settings)]):
            if "walltime" not in task:
                raise ValueError(f"{case}: each task must define walltime.")
            defaults = platform_list(task.get("platforms", [platform]))
            targets = override or defaults
            if platform not in targets:
                continue
            nodes = task.get("N_node", default_nodes) if N_node is None else N_node
            if type(nodes) is not int or nodes < 1:
                raise ValueError(f"{case}: N_node must be a positive integer.")
            if platform == "local" and N_node is None:
                nodes = 1
            limit = (
                1
                if platform == "local" or suite_dir.name == "serial"
                else PLATFORMS[platform]["max_nodes"]
            )
            if nodes > limit:
                raise ValueError(
                    f"{case}: N_node={nodes} exceeds the {limit}-node limit."
                )
            effective = {**task, "platforms": targets, "N_node": nodes}
            if nested:
                selected.setdefault(case, {})[mode] = effective
            else:
                selected[case] = effective
    return selected


def allocation_metadata(case_nodes, ranks_per_node):
    """Record scheduled case allocations and suite totals when uniform."""
    counts = set(case_nodes.values())
    uniform = counts.pop() if len(counts) == 1 else None
    return {
        "case_nodes": case_nodes,
        "case_processes": {
            case: nodes * ranks_per_node for case, nodes in case_nodes.items()
        },
        "N_node": uniform,
        "N_process": uniform * ranks_per_node if uniform else None,
    }
