"""Shared definitions for parallel-performance tasks."""

from pathlib import Path
import sys

import h5py

# Make shared performance helpers available when launching from this suite.
REPO_DIR = Path(__file__).resolve().parents[2]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from performance.metrics import output_complete, tally_score_paths
from configs.util import get_task_walltime, platform_names, platform_resources

NODE_COUNTS = (1, 2, 4, 8, 16, 32, 64, 128)
WORKLOAD_MULTIPLIERS = (1, 2, 4, 8, 16)


def _positive_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer; got {value!r}.")
    return value


def performance_task(case_name, N_particle_base, N_node, multiplier, platform="dane"):
    """Create one task dictionary for a performance matrix point."""
    N_particle_base = _positive_integer(N_particle_base, "N_particle_base")
    N_node = 1 if platform == "local" else _positive_integer(N_node, "N_node")
    multiplier = _positive_integer(multiplier, "multiplier")
    if platform not in platform_names():
        raise ValueError(f"Unknown platform: {platform!r}.")
    return {
        "case": case_name,
        "platform": platform,
        "N_particle_base": N_particle_base,
        "N_node": N_node,
        "workload_multiplier": multiplier,
        "N_particle": N_particle_base * N_node * multiplier,
        "total_multiplier": N_node * multiplier,
        "name": f"{case_name.replace('-', '_')}_{platform}_n{N_node:03d}_m{multiplier:02d}",
    }


def performance_tasks(config, N_node_max=128, platform="dane"):
    """Expand task.yaml into the node/workload matrix."""
    local = platform == "local"
    if local:
        N_node_max = 1
    _positive_integer(N_node_max, "N_node_max")
    if N_node_max not in NODE_COUNTS:
        raise ValueError(f"N_node_max must be one of {NODE_COUNTS}; got {N_node_max}.")

    tasks = []
    for case_name, settings in config.items():
        if (
            not isinstance(case_name, str)
            or Path(case_name).name != case_name
            or case_name in (".", "..")
        ):
            raise ValueError(f"Case must be a simple directory name: {case_name!r}.")
        if not isinstance(settings, dict) or "N_particle_base" not in settings:
            raise ValueError(
                f"Configuration for {case_name!r} requires N_particle_base."
            )
        if not local:
            if "walltime_factor" in settings:
                raise ValueError(
                    "Replace walltime_factor with a walltime workload mapping."
                )
            walltimes = settings.get("walltime")
            if not isinstance(walltimes, dict):
                raise ValueError(
                    f"{case_name} requires walltime hours for every workload multiplier."
                )
            for multiplier in WORKLOAD_MULTIPLIERS:
                if multiplier not in walltimes:
                    raise ValueError(
                        f"Missing walltime for {case_name}, multiplier {multiplier}."
                    )
                get_task_walltime({"walltime": walltimes[multiplier]})
        baseline = settings["N_particle_base"]
        if isinstance(baseline, dict):
            if platform not in baseline:
                raise ValueError(f"Missing {platform} baseline for {case_name}.")
            baseline = baseline[platform]
        N_particle_base = _positive_integer(
            baseline, f"{case_name} baseline particle count"
        )
        case_limit = 1 if local else settings.get("N_node", N_node_max)
        if case_limit not in NODE_COUNTS:
            raise ValueError(f"{case_name}: N_node must be one of {NODE_COUNTS}.")
        for N_node in NODE_COUNTS:
            if N_node > min(case_limit, N_node_max):
                continue
            for multiplier in WORKLOAD_MULTIPLIERS:
                task = performance_task(
                    case_name, N_particle_base, N_node, multiplier, platform
                )
                task["walltime"] = None if local else walltimes[multiplier]
                task["comparison"] = settings.get("comparison", case_name)
                task["method"] = settings.get("method", "Numba")
                if not isinstance(task["method"], str) or not task["method"].strip():
                    raise ValueError(
                        f"Method must be a nonempty label for {case_name}."
                    )
                tasks.append(task)
    return tasks


def case_directory(suite_directory, task):
    """Return the case directory shared by all its matrix points."""
    return Path(suite_directory) / "cases" / task["case"]


def output_name(task):
    """Return the unique case-local output name for one matrix point."""
    return f"output_{task['platform']}_n{task['N_node']:03d}_m{task['workload_multiplier']:02d}"


def output_directory(suite_directory, task):
    """Keep each platform's results separate from inputs and other platforms."""
    return case_directory(suite_directory, task) / "outputs" / task["platform"]


def task_output_complete(suite_directory, task):
    """Skip matching outputs but reject files from a different calibration."""
    path = output_directory(suite_directory, task) / f"{output_name(task)}.h5"
    if not output_complete(path):
        return False
    with h5py.File(path, "r") as output:
        ranks = task["N_node"] * platform_resources(task["platform"])["ranks_per_node"]
        if (
            int(output["settings/N_particle"][()].item()) != task["N_particle"]
            or int(output["performance/N_rank"][()].item()) != ranks
        ):
            raise ValueError(
                f"Existing output uses different launch settings: {path}. Move it aside before relaunching."
            )
    return True
