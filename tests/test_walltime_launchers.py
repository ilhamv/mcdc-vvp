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

    def test_root_platform_and_node_overrides(self):
        suite = SUITES[0]
        directory = self.root / suite
        task_file = directory / "task.yaml"
        original = yaml.safe_load(task_file.read_text())
        allocations = {
            "azurv1": (["dane"], 2),
            "reed": (["dane"], 4),
            "slab_absorbium": (["tuolumne"], 1),
        }
        tasks = {
            name: {**original[name], "platforms": platforms, "N_node": nodes}
            for name, (platforms, nodes) in allocations.items()
        }
        task_file.write_text(yaml.safe_dump(tasks))

        # Intercept the external scheduler at the executable boundary so that
        # the root launcher, child launcher and their argument parsing all run.
        executable = Path(self.directory.name) / "maestro"
        executable.write_text("#!/bin/sh\nmkdir -p maestro_run_fixture\n")
        executable.chmod(0o755)
        env = dict(
            os.environ,
            PATH=f"{executable.parent}{os.pathsep}{os.environ['PATH']}",
            PYTHONDONTWRITEBYTECODE="1",
        )
        for platforms, nodes, expected in [
            ([], None, {"azurv1": 2, "reed": 4}),
            (["dane"], None, {"azurv1": 2, "reed": 4, "slab_absorbium": 1}),
            (None, 3, {"azurv1": 3, "reed": 3}),
            (["dane"], 3, {"azurv1": 3, "reed": 3, "slab_absorbium": 3}),
        ]:
            with self.subTest(platforms=platforms, nodes=nodes):
                options = {"enabled": True, "platforms": platforms, "N_node": nodes}
                config = {suite: options}
                (self.root / "configs/launch_config.py").write_text(
                    f"LAUNCH_CONFIG = {config!r}\n"
                )
                result = subprocess.run(
                    [sys.executable, "launch.py", "--platform", "dane"],
                    cwd=self.root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                steps = yaml.safe_load((directory / "study.yaml").read_text())["study"]
                self.assertEqual(
                    {s["name"]: s["run"]["nodes"] for s in steps}, expected
                )
                self.assertEqual(
                    {s["name"]: s["run"]["procs"] for s in steps},
                    {name: count * 112 for name, count in expected.items()},
                )
                snapshot = yaml.safe_load(
                    (directory / "maestro_run_fixture/task.yaml").read_text()
                )
                self.assertEqual(set(snapshot), set(expected))

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
