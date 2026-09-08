# Parallel Performance

This suite measures MC/DC throughput, workload saturation, and parallel scaling across multiple compute nodes.
It uses one common automation workflow for all registered parallel-performance cases and can run independently or through the top-level MC/DC-VVP workflow.

## Directory layout

```text
cases/              Performance case definitions
  <problem>/
    <method>/
      input.py       Define and run one MC/DC model and method
      output_*.h5    Generated outputs for the scaling matrix
maestro_run_*/      Generated Maestro workflow directories
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

Each entry in `task.yaml` registers one problem and execution method.
Its value is the particle count calibrated to take approximately one hour on one full baseline node:

```yaml
<problem>:
  <method>: <baseline-particle-count>
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

## Adding a case

Create `cases/<problem>/<method>/input.py`, then add its calibrated baseline particle count to `task.yaml`.
The shared launcher expands every registered case over the same scaling matrix; no case-specific launch script is required.

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
Each task stores a runtime-only HDF5 result directly in its case directory.
Output names encode the node count and workload multiplier, for example `output_n004_m16.h5`.

After the jobs finish, run `python process.py`.
Each case receives a CSV table, a per-node performance envelope, a weak-scaling figure, and a strong-scaling figure under `results/<problem>/<method>/`.
Pass a `maestro_run_<timestamp>` directory to process a specific launch.

Run `python cleanup.py` to remove generated task outputs, Maestro records, processed results, and `study.yaml`.

## Cases

| Problem | Method | Description |
| :------ | :----- | :---------- |
| [`kobayashi`](cases/kobayashi/analog/) | Analog | Time-dependent Kobayashi dog-leg problem using standard analog transport. |
