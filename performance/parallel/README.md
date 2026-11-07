# Parallel Performance

Run full-node Numba CPU/GPU studies across platforms, node counts, workloads, and transport methods.
See the [complete parallel workflow](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/parallel.html) for configuration and processing details, and [performance interpretation](https://mcdc.readthedocs.io/en/dev/project/vvp/performance/index.html) for metrics, envelopes, and scaling summaries.

## Configure

Set baseline particles per batch in `task.yaml`:

```yaml
kobayashi-detector:
  method: Analog
  N_particle_base: 30_000_000
  walltime: {1: 1.5, 2: 3.0, 4: 6.0, 8: 12.0, 16: 24.0}
```

Calibrate for approximately one hour on one full node, including compilation and full tally output, with fixed batch count and physical problem. A scalar applies to every platform; a mapping under `N_particle_base` can instead supply a positive baseline per selected platform. Missing platform values raise an error.
The supplied [Kobayashi detector input](cases/kobayashi-detector/input.py) defines its materials directly.

The matrix combines power-of-two nodes through `N_node_max` with multipliers `1, 2, 4, 8, 16`. Particles per batch are `N_particle_base * N_node * multiplier`; required `walltime` maps each workload multiplier to explicit hours for that job. `--walltime` overrides every job uniformly. Requests are rounded up and capped at the platform maximum. Record calibration in task comments; the shown values carry forward the former requests pending recalibration.
CPU jobs use one rank per configured core; GPU jobs use one rank per GPU with `--target=gpu --gpu_state_storage=united`.

To compare methods, use the same `comparison` label and distinct `method` labels on equivalent observables, tally grids, normalization, and batch counts. Defaults are case name and `Numba`, respectively.

## Preview and launch

Run from this suite on each target machine. For example, preview without submission:

```bash
python launch.py --platform dane --N_node_max 128 --dry_run
```

For Tuolumne, use `--platform tuolumne`. Omit `--dry_run` to submit. Configure accounts/interpreters in `configs/user_config.py` and load the scheduler/GPU environment; Tuolumne may require ROCm and `flux env`.
The root launcher accepts the suite's `platforms` list and `N_node_max` and optional uniform `walltime` override from `configs/launch_config.py`.

Matching completed outputs are skipped. Incompatible baseline, rank-count, or tally content raises an error: preserve that campaign's outputs and saved metadata separately before launching a changed study.

Outputs follow `cases/<case>/outputs/<platform>/output_<platform>_n004_m16.h5`. Each invocation uses an isolated `workspaces/<platform>/<task>_*/` and cache directory shared by all its ranks/nodes. Resolve input data relative to `__file__` or by absolute paths. Outputs are written directly to their absolute destination.

## Process and inspect

Bring platform outputs and saved Maestro directories together under this suite before combining studies from different filesystems. Process the latest saved study per platform:

```bash
python process.py
```

Or select studies explicitly:

```bash
python process.py maestro_run_dane_<timestamp> maestro_run_tuolumne_<timestamp>
```

Processing uses saved configuration. Missing points are reported/skipped; duplicates, incompatible tallies, mismatched batch counts, and incorrect rank layouts are rejected. Legacy flat outputs need an explicitly identifying legacy study.

`results/studies/` retains configurations. Each `results/<comparison>/` contains `records.csv`, five metric plots (`runtime`, `tracking_rate`, `precision`, `precision_rate`, `fom`), `performance_envelope.png`, `scaling_summary.png`, and, when common coverage exists, `scaling_summary.csv`.

The summary requires common histories-per-node coverage and does not extrapolate. For a compatible factor-two workload matrix, select `--workload_factor 2 --workload_steps 4`. Inspect recorded interpolation brackets; collect overlap data or select compatible studies if no common range exists. The Sphinx guide explains main-bar/wing interpretation and unavailable metrics.

## Cleanup

After jobs stop, `python cleanup.py` removes outputs for all platforms, workspaces/caches, Maestro records, processed results, and generated study files. Inputs and `task.yaml` are retained.
