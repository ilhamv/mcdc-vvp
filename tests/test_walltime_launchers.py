"""Exercise actual study generation in isolated copies without submitting jobs."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    "verification/analytical/multigroup/fixed_source",
    "verification/analytical/multigroup/k_eigenvalue",
    "verification/code_to_code/multigroup/fixed_source",
    "validation/sinbad",
    "performance/serial",
    "performance/parallel",
)
HARNESS = """
import runpy, subprocess
from pathlib import Path
from unittest.mock import patch

real_run = subprocess.run

def fake_maestro(*args, **kwargs):
    command = args[0]
    if not any("maestro" in str(part) for part in command):
        return real_run(*args, **kwargs)
    (Path.cwd() / "maestro_run_dane_fixture").mkdir(exist_ok=True)
    return subprocess.CompletedProcess(args[0], 0)

with patch("subprocess.run", fake_maestro):
    runpy.run_path("launch.py", run_name="__main__")
"""


class LauncherWalltimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="vvp-walltime-tests-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "repo"
        shutil.copytree(
            ROOT,
            self.root,
            ignore=shutil.ignore_patterns(
                ".git",
                "__pycache__",
                "maestro_run_*",
                "results",
                "release",
                "outputs",
                "workspaces",
            ),
        )
        (self.root / "configs/user_config.py").write_text(
            'USER_CONFIG = {"dane": {"account": "test"}}\n'
        )

    def launch(self, suite, platform, override=None):
        args = [sys.executable, "-c", HARNESS, "--platform", platform]
        if override is not None:
            args += ["--walltime", str(override)]
        if suite == "performance/parallel":
            args += ["--N_node_max", "2", "--dry_run"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            args,
            cwd=self.root / suite,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )

    def test_uniform_override_in_every_suite(self):
        for suite in SUITES:
            with self.subTest(suite=suite):
                result = self.launch(suite, "dane", 2.25)
                self.assertEqual(result.returncode, 0, result.stderr)
                d = self.root / suite
                study = d / (
                    "study_dane.yaml"
                    if suite.startswith("performance/")
                    else "study.yaml"
                )
                steps = yaml.safe_load(study.read_text())["study"]
                self.assertTrue(steps)
                self.assertEqual({s["run"]["walltime"] for s in steps}, {"2:15:00"})
                if suite != "performance/parallel":
                    metadata = yaml.safe_load(
                        (d / "maestro_run_dane_fixture/launch_config.yaml").read_text()
                    )
                    self.assertEqual(metadata["walltime"], 2.25)

    def test_task_values_are_used_without_override(self):
        for suite in SUITES:
            with self.subTest(suite=suite):
                result = self.launch(suite, "dane")
                self.assertEqual(result.returncode, 0, result.stderr)
                d = self.root / suite
                study = d / (
                    "study_dane.yaml"
                    if suite.startswith("performance/")
                    else "study.yaml"
                )
                durations = {
                    s["run"]["walltime"]
                    for s in yaml.safe_load(study.read_text())["study"]
                }
                self.assertTrue(durations)
                if suite in (
                    SUITES[0],
                    SUITES[1],
                    "validation/sinbad",
                    "performance/parallel",
                ):
                    self.assertGreater(len(durations), 1)

    def test_missing_task_value_fails_even_locally_with_override(self):
        for suite in SUITES:
            with self.subTest(suite=suite):
                d = self.root / suite
                tasks = yaml.safe_load((d / "task.yaml").read_text())
                first = next(iter(tasks.values()))
                if suite == "validation/sinbad":
                    first = next(iter(first.values()))
                if suite == "performance/serial":
                    first = next(iter(first.values()))
                del first["walltime"]
                (d / "task.yaml").write_text(yaml.safe_dump(tasks))
                platform = "dane" if suite == "performance/parallel" else "local"
                result = self.launch(suite, platform, 2.25)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("walltime", result.stderr.lower())
                self.assertFalse((d / "maestro_run_dane_fixture").exists())


if __name__ == "__main__":
    unittest.main()
