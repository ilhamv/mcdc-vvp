"""Remove generated performance-study outputs and results."""

import shutil
from pathlib import Path

suite_dir = Path(__file__).resolve().parent
for runs_dir in suite_dir.glob("cases/*/*/runs"):
    if runs_dir.is_dir():
        shutil.rmtree(runs_dir)
for maestro_run in suite_dir.glob("maestro_run_*"):
    if maestro_run.is_dir():
        shutil.rmtree(maestro_run)
results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)
study_file = suite_dir / "study.yaml"
if study_file.is_file():
    study_file.unlink()
