"""Walltime configuration, scheduler formatting, and workload expansion contracts."""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configs.util import get_case_walltime, get_task_walltime

spec = importlib.util.spec_from_file_location(
    "parallel_task_util", ROOT / "performance/parallel/util.py"
)
parallel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parallel)
spec = importlib.util.spec_from_file_location(
    "sinbad_task_util", ROOT / "validation/sinbad/util.py"
)
sinbad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sinbad)


class WalltimeTests(unittest.TestCase):
    platform = {
        "max_walltime_hours": 24,
        "walltime_resolution_seconds": 60,
        "walltime_format": "{hours}:{minutes:02d}",
    }

    def test_task_hours_and_uniform_override(self):
        self.assertEqual(get_case_walltime({"walltime": 0.5}, self.platform), "0:30")
        for hours in (0.25, 6, 24):
            self.assertEqual(
                get_case_walltime({"walltime": hours}, self.platform, 2), "2:00"
            )

    def test_required_even_with_override(self):
        for override in (None, 2):
            with self.subTest(override=override), self.assertRaisesRegex(
                ValueError, "must define walltime"
            ):
                get_task_walltime({}, override)

    def test_invalid_task_and_override(self):
        for value in (None, True, False, 0, -1, "2", float("nan"), float("inf")):
            with self.subTest(task=value), self.assertRaises(ValueError):
                get_task_walltime({"walltime": value}, 2)
        for value in (True, 0, -1, "2", float("nan"), float("inf")):
            with self.subTest(override=value), self.assertRaises(ValueError):
                get_task_walltime({"walltime": 2}, value)

    def test_rounding_and_platform_cap(self):
        self.assertEqual(get_case_walltime({"walltime": 0.001}, self.platform), "0:01")
        self.assertEqual(get_case_walltime({"walltime": 25}, self.platform), "24:00")
        self.assertEqual(get_case_walltime({"walltime": 1}, self.platform, 30), "24:00")

    def test_legacy_factor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "walltime_factor"):
            get_task_walltime({"walltime": 2, "walltime_factor": 0.5})

    def test_explicit_workloads_and_no_implicit_formula(self):
        hours = {1: 0.2, 2: 0.7, 4: 1.1, 8: 2.2, 16: 3.9}
        tasks = parallel.performance_tasks(
            {"fixture": {"N_particle_base": 10, "walltime": hours}}, 2, "dane"
        )
        self.assertEqual(len(tasks), 10)
        for task in tasks:
            self.assertEqual(task["walltime"], hours[task["workload_multiplier"]])
            self.assertEqual(
                task["N_particle"], 10 * task["N_node"] * task["workload_multiplier"]
            )
            self.assertEqual(get_case_walltime(task, self.platform, 2), "2:00")

    def test_parallel_requires_every_workload(self):
        for hours in (None, 1.5, {1: 1.5}, {1: 1, 2: 2, 4: 4, 8: 8, 16: False}):
            with self.subTest(walltime=hours), self.assertRaises(ValueError):
                parallel.performance_tasks(
                    {"fixture": {"N_particle_base": 10, "walltime": hours}}, 1
                )

    def test_sinbad_requires_positive_hours(self):
        import tempfile
        import yaml

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.yaml"
            for hours in (None, 0, False, float("nan"), 0.24):
                path.write_text(
                    yaml.safe_dump(
                        {"fng-tud-sic": {"p1": {"N_particle": 10, "walltime": hours}}}
                    )
                )
                if hours == 0.24:
                    _, tasks = sinbad.load_tasks(path)
                    self.assertEqual(get_task_walltime(tasks[0][2]), 0.24)
                else:
                    with self.subTest(walltime=hours), self.assertRaises(ValueError):
                        sinbad.load_tasks(path)


if __name__ == "__main__":
    unittest.main()
