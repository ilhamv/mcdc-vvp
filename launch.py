"""Launch the configured MC/DC VVP suites."""

import argparse
import subprocess
import sys
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

for suite, options in LAUNCH_CONFIG.items():
    platforms = options.get("platforms")
    if (
        not isinstance(platforms, list)
        or not platforms
        or not all(isinstance(platform, str) and platform for platform in platforms)
    ):
        parser.error(
            f"Suite '{suite}' must define 'platforms' as a nonempty list of "
            "platform names in configs/launch_config.py."
        )

# Select only suites assigned to this launch invocation.
selected_suites = {
    suite: options
    for suite, options in LAUNCH_CONFIG.items()
    if options.get("enabled", False) and active_platform in options["platforms"]
}
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

    if options.get("N_node") is not None:
        command.extend(["--N_node", str(options["N_node"])])

    if options.get("walltime") is not None:
        command.extend(["--walltime", str(options["walltime"])])

    if options.get("N_node_max") is not None:
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
