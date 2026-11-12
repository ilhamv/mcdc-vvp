# Serial Performance

This suite measures Python and Numba performance with one process per job.
See the [serial performance guide](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/serial.html) for scheduled runs and the [performance metrics](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/index.html) for interpreting the plots.

## Quick run

To compare both modes at 10 and 100 particles per batch, set [task.yaml](task.yaml) to the following.

```yaml
kobayashi-detector:
  python:
    logN_min: 1
    logN_max: 2
    N_task: 2
  numba:
    logN_min: 1
    logN_max: 2
    N_task: 2
```

From this suite directory, launch the local study.

```bash
python launch.py
```

When both modes finish, run `python process.py` and open `results/local/kobayashi-detector/` for `records.csv` and the metric plots.
