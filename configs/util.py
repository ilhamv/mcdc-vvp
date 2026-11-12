"""Read and resolve platform, user, and launch settings for VVP campaigns."""

import math
import os
import sys
from pathlib import Path

import yaml

from configs.platform_config import PLATFORMS

# ======================================================================================
# Campaign and suite selection
# ======================================================================================


def get_launch_config():
    """Read the configured suites when running a campaign entry point."""
    from configs.launch_config import LAUNCH_CONFIG

    return LAUNCH_CONFIG


def suite_launch_args(platform):
    """Select enabled suites and build their command-line overrides."""
    selected = {}
    for suite, options in get_launch_config().items():
        if not options.get("enabled", False):
            continue
        args = ["--platform", platform]
        if platform != "local":
            nodes = options.get("N_node")
            if nodes is None:
                nodes = options.get("N_node_max")
            if nodes is not None:
                args.extend(["--N_node", str(nodes)])
            if options.get("walltime") is not None:
                args.extend(["--walltime", str(options["walltime"])])
        selected[suite] = args
    return selected


# ======================================================================================
# Platform choices and task resources
# ======================================================================================


def platform_names(include_local=True):
    """Return platforms available to a launcher."""
    return ("local", *PLATFORMS) if include_local else tuple(PLATFORMS)


def load_suite_tasks(suite_dir, platform, N_node=None):
    """Read a suite's task.yaml and apply the launch overrides."""
    with (suite_dir / "task.yaml").open() as stream:
        config = yaml.safe_load(stream)
    return resolve_task_resources(config, suite_dir, platform, N_node)


def resolve_task_resources(config, suite_dir, platform, N_node=None):
    """Resolve the node count for every configured task on the chosen platform."""
    default_nodes = 128 if suite_dir.name == "parallel" else 1
    nested = suite_dir.name in {"sinbad", "serial"}
    selected = {}
    for case, settings in config.items():
        for mode, task in (settings.items() if nested else [(None, settings)]):
            if platform == "local":
                effective = {**task, "N_node": 1}
                effective.pop("walltime", None)
            else:
                if "walltime" not in task:
                    raise ValueError(
                        f"{case}: each scheduled task must define walltime."
                    )
                nodes = task.get("N_node", default_nodes) if N_node is None else N_node
                if type(nodes) is not int or nodes < 1:
                    raise ValueError(f"{case}: N_node must be a positive integer.")
                limit = (
                    1
                    if suite_dir.name == "serial"
                    else get_platform(platform)["max_nodes"]
                )
                if nodes > limit:
                    raise ValueError(
                        f"{case}: N_node={nodes} exceeds the {limit}-node limit."
                    )
                effective = {**task, "N_node": nodes}
            if nested:
                selected.setdefault(case, {})[mode] = effective
            else:
                selected[case] = effective
    return selected


# ======================================================================================
# Platform resources and user settings
# ======================================================================================


def get_platform(name):
    """Return hardware and scheduler settings for a platform."""
    if name == "local":
        return {
            "host": "local",
            "scheduler": "local",
            "cpu_cores_per_node": 1,
            "gpus_per_node": 0,
            "max_nodes": 1,
        }
    return PLATFORMS[name]


def get_user_config(platform_name):
    """Resolve account settings and Python interpreters for this platform."""
    try:
        from configs.user_config import USER_CONFIG
    except ModuleNotFoundError as error:
        if error.name != "configs.user_config":
            raise
        USER_CONFIG = {}

    settings = USER_CONFIG.get(platform_name, {})
    python = settings.get("mcdc_python")
    maestro = settings.get("maestro_python") if platform_name != "local" else None
    return {
        "account": settings.get("account"),
        "queue": settings.get("queue"),
        "reservation": settings.get("reservation"),
        "mcdc_python": (
            sys.executable if python is None else str(Path(python).expanduser())
        ),
        "maestro_python": None if maestro is None else str(Path(maestro).expanduser()),
    }


def get_batch_config(platform, user, dry_run=False):
    """Build the Maestro batch settings for a scheduled study."""
    if platform["scheduler"] == "local":
        return {}
    account = user.get("account")
    if account is None:
        if not dry_run:
            raise ValueError(
                f"Platform '{platform['host']}' requires an account. "
                "Create configs/user_config.py from configs/user_config.py.template."
            )
        account = "UNCONFIGURED"
    batch = {"type": platform["scheduler"], "host": platform["host"], "bank": account}
    for key in ("queue", "reservation"):
        if user.get(key) is not None:
            batch[key] = user[key]
    return batch


def platform_resources(platform_name):
    """Choose one rank per GPU or one rank per CPU core for a scaling study."""
    platform = get_platform(platform_name)
    gpus = platform["gpus_per_node"]
    return {
        "target": "gpu" if gpus else "cpu",
        "ranks_per_node": gpus or platform["cpu_cores_per_node"],
        "gpus_per_node": gpus,
    }


# ======================================================================================
# Job walltime
# ======================================================================================


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


# ======================================================================================
# Maestro invocation and allocation metadata
# ======================================================================================


def maestro_command(user, study_name):
    """Build the Maestro invocation and its environment for the chosen interpreter."""
    env = os.environ.copy()
    python = user["maestro_python"]
    if python is None:
        return ["maestro", "run", study_name], env
    env["PATH"] = os.pathsep.join(
        (str(Path(python).parent), env.get("PATH", os.defpath))
    )
    return [python, "-m", "maestrowf.maestro", "run", study_name], env


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


# ======================================================================================
# Result processing
# ======================================================================================


def get_sinbad_root(repo_dir, suite, options):
    """Resolve a configured SINBAD package path relative to the repository."""
    path = options.get("sinbad_root")
    if path is None:
        if suite == "validation/sinbad":
            raise ValueError(
                "Set validation/sinbad sinbad_root in configs/launch_config.py before processing the SINBAD suite."
            )
        return None
    return repo_dir / Path(path).expanduser()
