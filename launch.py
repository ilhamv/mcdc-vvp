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

from configs.util import suite_launch_args

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

selected_suites = suite_launch_args(REPO_DIR, active_platform)
if not selected_suites:
    parser.error(f"No enabled suites are configured for platform '{active_platform}'.")


# ======================================================================================
# Launch enabled, compatible suites
# ======================================================================================

for suite, arguments in selected_suites.items():
    suite_dir = REPO_DIR / suite
    launcher = suite_dir / "launch.py"

    if not suite_dir.is_dir():
        raise FileNotFoundError(f"Suite directory not found: {suite_dir}")

    if not launcher.is_file():
        raise FileNotFoundError(f"Suite launcher not found: {launcher}")

    # Reuse the active interpreter so suite launchers inherit this environment.
    command = [sys.executable, str(launcher), *arguments]

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
