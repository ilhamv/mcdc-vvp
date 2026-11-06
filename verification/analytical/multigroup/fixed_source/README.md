# Analytical Multigroup Fixed-Source Verification

Run this suite independently or through the repository-wide launcher.
The [suite documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/analytical/multigroup/fixed_source/index.html) contains the case catalog, problem definitions, references, and interpretation. See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for the complete operating guide.

## Configure

Select cases in `task.yaml` using `logN_min`, `logN_max`, `N_task`, and optional `walltime_factor`:

```yaml
azurv1:
  logN_min: 5
  logN_max: 7
  N_task: 7
  walltime_factor: 0.45
```

The runner generates logarithmically spaced particle counts and runs each case's tasks sequentially. SHEM-361 inputs use `data/SHEM-361.npz`.

## Launch and resume

Run commands from this suite directory. Choose local execution:

```bash
python launch.py
```

Or launch on the configured HPC platform:

```bash
python launch.py --platform tuolumne --N_node 1 --walltime 1.0
```

`N_node` sets nodes per case, using the configured CPU cores on each node. `--walltime` is a base duration in hours, scaled by each case's `walltime_factor`, rounded up to scheduler resolution, and capped at the platform limit. Local execution ignores walltime.
Shared platform and account/interpreter settings come from the repository's `configs/` directory.

Completed task outputs are skipped on relaunch; complete cases are omitted from the study. Preserve old outputs separately before changing the problem or sampling configuration.

## Process

After jobs finish, process the latest saved study:

```bash
python process.py
```

Or select one explicitly:

```bash
python process.py maestro_run_<timestamp>
```

Processing uses the saved launch/task configurations. Keep the saved study and its outputs together.

## Outputs and inspection

- `cases/<case>/output_<N_particle>.h5`: simulation results.
- `results/convergence/`: convergence figures.
- `results/comparison/`: largest-sample comparisons and transient animations.

`results/launch_config.yaml` and `results/task.yaml` preserve the processed configuration. The root processor moves suite results under the same suite path in the repository's `results/` tree.

## Cleanup

After jobs stop, `python cleanup.py` removes case outputs, processed results, Maestro directories, and the generated `study.yaml`. Inputs and reference data are retained.
