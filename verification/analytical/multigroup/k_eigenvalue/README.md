# Analytical Multigroup k-Eigenvalue Verification

Run this suite independently or through the repository-wide launcher.
The [suite documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/analytical/multigroup/k_eigenvalue/index.html) contains the case catalog, problem definitions, references, and interpretation. See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for the complete operating guide.

## Configure

Select cases in `task.yaml` using `N_active_min`, `N_active_max`, `N_task`, and required `walltime` in hours:

```yaml
one_group_slab:
  N_active_min: 20
  N_active_max: 2000
  N_task: 5
  walltime: 0.21
```

Tasks vary geometrically spaced active-cycle counts. Particles per cycle and inactive cycles are fixed in each `input.py`; establish them with a preliminary source-convergence study. Multigroup data are shared at `../fixed_source/data/SHEM-361.npz`.

## Launch and resume

Run commands from this suite directory. Choose local execution:

```bash
python launch.py
```

Or launch on the configured HPC platform:

```bash
python launch.py --platform tuolumne --N_node 1 --walltime 1.0
```

`N_node` sets nodes per case, using the configured CPU cores on each node. Required `walltime` in `task.yaml` specifies hours for the entire case job. `--walltime` overrides all job durations uniformly; requests are rounded up and capped at the platform limit. Local execution ignores the limit but still requires a valid task value.
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

- `cases/<case>/output_<N_active>.h5`: simulation results.
- `results/convergence/`: active-cycle convergence and uncertainty plots.
- `results/comparison/`: largest-sample flux shapes and cycle histories.

To inspect one result:

```bash
python cases/inf_shem361_subcritical/plot.py cases/inf_shem361_subcritical/output_2000.h5
```

`results/launch_config.yaml` and `results/task.yaml` preserve the processed configuration. The root processor moves suite results under the same suite path in the repository's `results/` tree.

## Cleanup

After jobs stop, `python cleanup.py` removes case outputs, processed results, Maestro directories, and the generated `study.yaml`. Inputs and reference data are retained.
