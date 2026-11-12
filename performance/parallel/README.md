# Parallel Performance

This suite measures how Numba performance changes with workload and node count on CPU and GPU platforms.
See the [parallel performance guide](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/parallel.html) for platform-specific baselines, cross-platform comparisons, and scaling plots.

## Quick run

Configure your platform as shown in the [repository quick start](../../README.md#quick-run-on-a-platform).
From this suite directory, preview a one- and two-node study using the baseline and walltimes in [task.yaml](task.yaml), substituting your platform name for `dane`.

```bash
python launch.py --platform dane --N_node_max 2 --dry_run
```

Each node count runs five workloads at 1, 2, 4, 8, and 16 times the baseline particles per node.
Remove `--dry_run` to submit the jobs.
After they finish, run `python process.py` and open `results/kobayashi-detector/` for `records.csv` and the scaling plots.
