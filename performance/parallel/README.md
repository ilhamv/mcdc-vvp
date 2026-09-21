# Parallel Performance

This suite measures MC/DC runtime, tracking rate, precision, precision rate, figure of merit, and parallel scaling across multiple compute nodes in Numba mode.
It uses one common automation workflow for all registered parallel-performance cases and can run independently or through the top-level MC/DC-VVP workflow.

## Directory layout

```text
cases/              Performance case definitions
  <case>/
    input.py         Define and run one MC/DC model
    output_*.h5      Generated outputs including full tally results
maestro_run_*/      Generated Maestro workflow directories
workspaces/         Isolated per-launch working directories and caches
results/            Processed tables and scaling figures

task.yaml           Configure the baseline particle count for each case
study.yaml          Generated Maestro study definition

launch.py           Build and launch the Maestro study
run_case.py         Run one scaling-matrix point
process.py          Process completed scaling tasks

cleanup.py          Remove generated outputs and results
util.py             Provide shared task-generation utilities
```

## Configuration

Each entry in `task.yaml` registers one case.
Its `N_particle_base` is the particles per batch calibrated to take approximately one hour on one full baseline node, with the input's batch count and full tally output:

```yaml
<case>:
  N_particle_base: <baseline-particle-count>
```

The shared input matrix contains node counts `1, 2, 4, 8, 16, 32, 64` and per-node workload multipliers `1, 2, 4, 8, 16`.
For every matrix point,

```text
N_particle = baseline-particle-count * nodes * workload-multiplier
```

Every point is an independent Maestro step and batch job.
A job receives exclusive nodes and fills every CPU core configured for the platform.
The requested walltimes are `1.5, 3, 6, 12, 24` hours for workload multipliers `1, 2, 4, 8, 16`, respectively.

The five fixed-multiplier columns form weak-scaling series.
Points with equal `nodes * workload-multiplier` form strong-scaling series.
The input file remains the source of truth for settings such as `N_batch`.
The current `kobayashi-detector` baseline of `1_000_000` is a placeholder that must be calibrated before the full study; the former analog case's calibration does not apply.
The detector input matches the serial case, including 30 batches and implicit capture.
The current case defines its multigroup materials directly and needs no external data directory.
HPC runs use the shared platform settings in `configs/platform_config.py` and account, queue, reservation, and Python paths in `configs/user_config.py`.
The launcher currently supports full-CPU Dane runs.

## Adding a case

Create `cases/<case>/input.py`, then add its calibrated baseline particle count to `task.yaml`.
The shared launcher expands every registered case over the same scaling matrix; no case-specific launch script is required.
Resolve input data paths relative to `__file__` or use absolute paths, since simulations do not run from the case directory.

## Launching and processing

Generate `study.yaml` without submitting jobs:

```console
python launch.py --platform dane --N_node_max 64 --dry_run
```

Launch the study:

```console
python launch.py --platform dane --N_node_max 64
```

Completed matrix points are skipped on relaunch.
Each invocation creates a unique working directory under `workspaces/`, including retries of an unfinished matrix point.
The simulation uses this directory for its generated GPU-code cache and a job-specific `NUMBA_CACHE_DIR`, preventing simultaneous jobs from clearing or overwriting each other's caches.
All MPI ranks of one job share the same directory; the suite must reside on a filesystem accessible from every allocated node.
Input and output paths are absolute, so the input stays in its case directory and HDF5 output names and processing remain unchanged.
Working directories are retained after success or failure for inspection and removed by `cleanup.py`.
Each task stores an HDF5 result directly in its case directory, including full tally results, standard metadata, runtime details, and the `performance/` group.
Numba caching is disabled, consistent with the serial suite, and all runtime-dependent metrics use measured total runtime without subtracting compilation or other overhead.
Output names encode the node count and workload multiplier, for example `output_n004_m16.h5`.

After the jobs finish, run `python process.py`.
Each case receives `records.csv` and eight figures under `results/<case>/`.
The five log-log plots against total histories are `runtime.png`, `tracking_rate.png`, `precision.png`, `precision_rate.png`, and `fom.png`, with a separate curve for each node count.
The existing `performance_envelope.png`, `weak_scaling.png`, and `strong_scaling.png` show per-node tracking rate and scaling efficiencies.
Tracking rates and scaling efficiencies use total runtime from `performance/runtime`, including compilation and output work.
History counts come from `performance/N_history`, rather than being inferred from the input file.
For each case, all node counts use the same reference: the available configured output with the largest total history count, preferring fewer nodes on a tie.
The maximum relative variance is $V_{\max}=\max_{i:\mu_{i,\mathrm{ref}}\ne 0}(s_i/\mu_{i,\mathrm{ref}})^2$, where $s_i$ is the current run's tally standard error (`sdev`).
The maximum includes all tally scores and all bins with nonzero reference means, even if the current run's mean is zero.
Tally scores, grids, shapes, and batch counts must match across matrix points, and rank counts must match the full-node configuration saved for the launch.
The shared calculation in `../metrics.py` is also used by the serial suite.
With $V_{\%,\max}=10^4 V_{\max}$, precision is $1/V_{\%,\max}$ in $\%^{-2}$, precision rate is $1/(V_{\%,\max}N)$ in $\%^{-2}$ per history, and FOM is $1/(TV_{\%,\max})$ in $\%^{-2}$ per second.
FOM is the product of tracking rate and precision rate.
These three metrics use total runtime and histories for the whole job, not per-node normalization.
The CSV also records the reference node/multiplier and particle/history counts, `N_reference_nonzero_bin`, fractional `max_relative_variance`, `performance/N_rank`, and the runtime breakdown.
The original `performance/effective_variance` is retained for comparison but not used for plotting.
If no reference bins have nonzero means, or the maximum variance is nonfinite or nonpositive, derived precision metrics are recorded as `nan` and omitted from curves.
An entirely unavailable metric gets an explanatory message in its figure.
Pass a `maestro_run_<timestamp>` directory to process a specific launch.
Processing uses that run's saved task and launch configuration and skips missing matrix points.
Scaling efficiencies are normalized to the smallest available node count in each series.
Outputs without full tally results are rejected rather than reused or overwritten; move them aside before relaunching.
Measurements from runs that omitted tally output or enabled caching represent a different workload.
Older saved tasks using the problem/method layout are not compatible with this case layout.

Run `python cleanup.py` after all jobs have stopped to remove generated task outputs, working directories and caches, Maestro records, processed results, and `study.yaml`.
The study file is untracked and regenerated by `launch.py` for the selected platform.

## Cases

| Case | Description |
| :--- | :---------- |
| [`kobayashi-detector`](cases/kobayashi-detector/) | Transient Kobayashi dog-leg problem with a fuel cube and detector capture tally. |
