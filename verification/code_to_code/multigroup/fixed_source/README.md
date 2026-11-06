# Code-to-Code Multigroup Fixed-Source Verification

Run this suite independently or through the repository-wide launcher.
The [suite documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/code_to_code/multigroup/fixed_source/index.html) contains the case catalog, problem definitions, references, and interpretation. See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for the complete operating guide.

## Configure

Select cases in `task.yaml` using `logN_min`, `logN_max`, `N_task`, and `walltime_factor`. Tasks vary particles per batch; `input.py` defines the batch count, which must match the participating-code comparison data. The supplied cases use 30 batches.
C5G7 uses `data/MGXS-C5G7.h5`.

Download and checksum external OpenMC statepoints before processing:

```bash
python cases/c5g7-4phase/reference.py
python cases/kobayashi/reference.py
```

The `kobayashi-detector` downloader still points to a baseline archive placeholder. Supply detector-specific reference outputs before processing that case; baseline flux statepoints are not detector-capture references.

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

- `cases/<case>/output_<N_particle>.h5`: MC/DC results.
- `cases/<case>/reference/`: participating-code comparison files.
- `results/convergence/`: pairwise convergence figures.
- `results/reference/`: fixed-reference figures and animations.
- `results/comparison/`: largest-shared-sample comparisons and differences.

To inspect a baseline Kobayashi sampling point:

```bash
python cases/kobayashi/plot.py \
    cases/kobayashi/output_100000000.h5 \
    cases/kobayashi/reference/output_0.h5 \
    cases/kobayashi/output_10000000000.h5 \
    cases/kobayashi/reference/output_4.h5
```

`results/launch_config.yaml` and `results/task.yaml` preserve the processed configuration. The root processor moves suite results under the same suite path in the repository's `results/` tree.

## Cleanup

After jobs stop, `python cleanup.py` removes case outputs, processed results, Maestro directories, and the generated `study.yaml`. Inputs and reference data are retained.
