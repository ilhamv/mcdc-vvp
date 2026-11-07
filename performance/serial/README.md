# Serial Performance

Run Python and/or Numba sampling studies with one process per job, locally or on one exclusive cluster node.
The [complete serial workflow](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/serial.html) covers operation and records; [performance definitions and interpretation](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/index.html) explain the metrics.

## Configure

Each `task.yaml` case has a `numba` block, a `python` block, or both:

```yaml
kobayashi-detector:
  numba:
    logN_min: 1
    logN_max: 6
    N_task: 11
    walltime: 24.0
  python:
    logN_min: 1
    logN_max: 4
    N_task: 7
    walltime: 24.0
```

Omit a mode to disable it. Each case-mode job runs its own sampling points sequentially; modes schedule independently. Each mode block requires `walltime` in hours. Batch counts come from `input.py`.
The supplied [Kobayashi detector input](cases/kobayashi-detector/input.py) defines its multigroup materials directly.

## Launch and resume

From this suite directory, choose local execution:

```bash
python launch.py
```

Or use the configured cluster:

```bash
python launch.py --platform dane --walltime 1.0
```

Each cluster job requests one process on one exclusive node. Each mode block requires `walltime` in hours; `--walltime` overrides all jobs uniformly. Requests are rounded up and capped at the platform maximum. Local runs ignore the limit but require valid values.

Outputs are stored as `cases/<case>/outputs/<platform>/output_<mode>_<N_particle>.h5`. Completed compatible outputs are skipped independently per mode. Outputs must contain full tallies; preserve incompatible older outputs separately before regenerating them.
Caching is disabled, and measured runtime includes compilation and full tally output.

## Process and inspect

After completion, process the latest saved study per platform:

```bash
python process.py
```

Or select saved studies:

```bash
python process.py maestro_run_dane_<timestamp> maestro_run_local_<timestamp>
```

Processing uses saved `task.yaml`, not the current file. Older saved schemas using shared bounds or `python_mode` require conversion to the nested mode-block format.
Outputs must have one MPI rank; matching particle counts across modes must have matching history and batch counts and compatible tally grids/scores. Missing mode points do not discard the other mode's measurements. At least one configured point must be available.

`results/<platform>/<case>/` contains `records.csv`, `runtime.png`, `tracking_rate.png`, `precision.png`, `precision_rate.png`, and `fom.png`. Records identify the reference and unavailable values; see the Sphinx guide for definitions and plotting conventions.

## Cleanup

After jobs stop, `python cleanup.py` removes generated outputs, Maestro records, processed results, and platform-specific study files. Inputs and task settings are preserved.
