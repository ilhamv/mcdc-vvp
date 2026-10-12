"""Remove generated serial-performance outputs and results."""

import shutil
from pathlib import Path

suite_dir = Path(__file__).resolve().parent
cases_dir = suite_dir / "cases"
# Remove simulation outputs while preserving case inputs and shared data.
for output_file in cases_dir.glob("*/output*.h5"):
    output_file.unlink()
for outputs_dir in cases_dir.glob("*/outputs"):
    if outputs_dir.is_dir():
        shutil.rmtree(outputs_dir)
# Remove generated Maestro workflow directories.
for maestro_run in suite_dir.glob("maestro_run_*"):
    if maestro_run.is_dir():
        shutil.rmtree(maestro_run)
# Remove the complete processed-results hierarchy.
results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)
# Remove the generated Maestro study definition.
for study_file in suite_dir.glob("study*.yaml"):
    study_file.unlink()
