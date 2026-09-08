"""Shared definitions for parallel-performance tasks."""

from pathlib import Path

NODE_COUNTS = (1, 2, 4, 8, 16, 32, 64)
WORKLOAD_MULTIPLIERS = (1, 2, 4, 8, 16)
WALLTIME_BASE_HOURS = 1.5


def _positive_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer; got {value!r}.")
    return value


def performance_task(problem, method, N_particle_base, N_node, multiplier):
    """Create one task dictionary for a performance matrix point."""
    N_particle_base = _positive_integer(N_particle_base, "N_particle_base")
    N_node = _positive_integer(N_node, "N_node")
    multiplier = _positive_integer(multiplier, "multiplier")
    return {
        "problem": problem,
        "method": method,
        "N_particle_base": N_particle_base,
        "N_node": N_node,
        "workload_multiplier": multiplier,
        "N_particle": N_particle_base * N_node * multiplier,
        "total_multiplier": N_node * multiplier,
        "walltime_hours": WALLTIME_BASE_HOURS * multiplier,
        "name": f"{problem}_{method}_n{N_node:03d}_m{multiplier:02d}",
    }


def performance_tasks(config, N_node_max=64):
    """Expand task.yaml into the node/workload matrix."""
    _positive_integer(N_node_max, "N_node_max")
    if N_node_max not in NODE_COUNTS:
        raise ValueError(f"N_node_max must be one of {NODE_COUNTS}; got {N_node_max}.")

    tasks = []
    for problem, methods in config.items():
        if not isinstance(methods, dict):
            raise ValueError(f"Configuration for {problem!r} must be a mapping.")
        for method, N_particle_base in methods.items():
            N_particle_base = _positive_integer(
                N_particle_base, f"{problem}/{method} baseline particle count"
            )
            for N_node in NODE_COUNTS:
                if N_node > N_node_max:
                    continue
                for multiplier in WORKLOAD_MULTIPLIERS:
                    tasks.append(
                        performance_task(
                            problem,
                            method,
                            N_particle_base,
                            N_node,
                            multiplier,
                        )
                    )
    return tasks


def case_directory(suite_directory, task):
    return Path(suite_directory) / "cases" / task["problem"] / task["method"]


def output_name(task):
    """Return the unique case-local output name for one matrix point."""
    return f"output_n{task['N_node']:03d}_m{task['workload_multiplier']:02d}"
