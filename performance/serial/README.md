# Serial Performance

This suite compares MC/DC runtime and tracking rate in Python and Numba modes using one process.
It can run locally or on one exclusive cluster node through the top-level MC/DC-VVP workflow.

## Directory layout

```text
cases/              Serial performance case definitions
  <case>/
    input.py         Define and run one MC/DC model
    output_*.h5      Generated runtime-only outputs
maestro_run_*/      Generated Maestro workflow directories
results/            Processed tables and performance figures

task.yaml           Configure the particle-count study for each case
study.yaml          Generated Maestro study definition

launch.py           Build and launch the Maestro study
run_case.py         Run one case in Python and Numba modes
process.py          Generate runtime and tracking-rate results

cleanup.py          Remove generated outputs and results
util.py             Provide shared task-generation utilities
```

## Configuration

Each `task.yaml` entry defines logarithmic particle-count bounds, the number of sampling points, and a walltime factor.
The input file remains the source of truth for `N_batch`, so the number of histories is `N_particle * N_batch`.

Each sampling point runs once in Python mode and once in Numba mode.
Every run uses `--runtime_output`, so its HDF5 file contains only the existing MC/DC runtime datasets.
Output names encode the mode and particle count, for example `output_numba_10000.h5`.
Numba caching remains disabled so every Numba measurement includes compilation.
Cluster execution requests one process on one exclusive node.

## Launching and processing

From this suite directory, launch locally:

```console
python launch.py
```

Launch on a supported cluster:

```console
python launch.py --platform dane --walltime 1.0
```

Completed mode and particle-count outputs are skipped on relaunch.
Run `python process.py` after the jobs finish.
Pass a `maestro_run_<timestamp>` directory to process a specific launch.

For each case, processing creates `records.csv`, `runtime.png`, and `tracking_rate.png`.
The runtime is the total MC/DC runtime, including Numba compilation.
The tracking rate is the number of histories divided by total runtime.
The Numba compilation time is estimated as the median of the three smallest-history Numba runtimes.
The compilation-adjusted Numba series subtracts that estimate from each Numba runtime.

Run `python cleanup.py` to remove generated outputs, Maestro records, processed results, and `study.yaml`.

## Cases

| Case | Description |
| :--- | :---------- |
| [`c5g7-4phase`](cases/c5g7-4phase/) | Four-phase C5G7 transient problem. |
| [`kobayashi`](cases/kobayashi/) | Time-dependent Kobayashi dog-leg problem. |
