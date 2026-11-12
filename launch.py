"""Launch the configured MC/DC VVP suites."""

import argparse
import subprocess
import sys

import yaml
from pathlib import Path

# ======================================================================================
# Bootstrap VVP imports
# ======================================================================================

REPO_DIR = Path(__file__).resolve().parent

# Support launching this script from any working directory without installing VVP.
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


# ======================================================================================
# Load launch configuration
# ======================================================================================

from configs.launch_config import LAUNCH_CONFIG
from configs.util import select_tasks

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="Launch enabled MC/DC VVP suites.")
parser.add_argument(
    "--platform",
    default="local",
    help="Launch enabled suites that list PLATFORM (default: local).",
)
args = parser.parse_args()

active_platform = args.platform

selected_suites = {}
for suite, options in LAUNCH_CONFIG.items():
    if not options.get("enabled", False):
        continue
    suite_dir = REPO_DIR / suite
    with (suite_dir / "task.yaml").open() as stream:
        config = yaml.safe_load(stream)
    nodes = options.get("N_node")
    if nodes is None:
        nodes = options.get("N_node_max")
    if select_tasks(
        config, suite_dir, active_platform, options.get("platforms"), nodes
    ):
        selected_suites[suite] = options
if not selected_suites:
    parser.error(f"No enabled suites are configured for platform '{active_platform}'.")


# ======================================================================================
# Launch enabled, compatible suites
# ======================================================================================

for suite, options in selected_suites.items():
    suite_dir = REPO_DIR / suite
    launcher = suite_dir / "launch.py"

    if not suite_dir.is_dir():
        raise FileNotFoundError(f"Suite directory not found: {suite_dir}")

    if not launcher.is_file():
        raise FileNotFoundError(f"Suite launcher not found: {launcher}")

    # Reuse the active interpreter so suite launchers inherit this environment.
    command = [sys.executable, str(launcher)]

    # Forward only options that are meaningful for the configured suite.
    command.extend(["--platform", active_platform])

    if options.get("platforms"):
        command.extend(["--platforms", *options["platforms"]])

    if options.get("N_node") is not None:
        command.extend(["--N_node", str(options["N_node"])])

    if options.get("walltime") is not None:
        command.extend(["--walltime", str(options["walltime"])])

    if options.get("N_node") is None and options.get("N_node_max") is not None:
        command.extend(["--N_node_max", str(options["N_node_max"])])

    print("=" * 80)
    print(f"Launching suite: {suite}")
    print("Command:", " ".join(command))
    print("=" * 80)

    subprocess.run(command, cwd=suite_dir, check=True)


# ======================================================================================
# Summary
# ======================================================================================

print()
print("Launch complete.")
