# Serial Performance

This suite measures MC/DC runtime, tracking rate, precision, precision rate, and figure of merit in Numba mode, optionally comparing Python mode, using one process.
It can run locally or on one exclusive cluster node through the top-level MC/DC-VVP workflow.

## Directory layout

```text
cases/              Serial performance case definitions
  <case>/
    input.py         Define and run one MC/DC model
    output_*.h5      Generated outputs without tally results
data/               Shared multigroup cross-section data
maestro_run_*/      Generated Maestro workflow directories
results/            Processed tables and performance figures

task.yaml           Configure the particle-count study for each case
study.yaml          Generated Maestro study definition

launch.py           Build and launch the Maestro study
run_case.py         Run one case in its enabled execution modes
process.py          Generate runtime, precision, and figure-of-merit results

cleanup.py          Remove generated outputs and results
util.py             Provide shared task-generation utilities
```

## Configuration

Each `task.yaml` entry defines logarithmic particle-count bounds, the number of sampling points, and a walltime factor.
Each case is one Maestro step that runs its sampling points and enabled execution modes sequentially.
The launch-level `--walltime` is specified in hours and multiplied by each case's `walltime_factor`.
The result is rounded up to the scheduler resolution and capped at the platform maximum.
When `--walltime` is omitted, the platform maximum is used as the base; local runs ignore walltime.
For example, `--walltime 1.0` requests six hours for C5G7 and one hour for Kobayashi with the current task settings.
The input file defines settings such as `N_batch`; processing reads the actual settings and total history count from each output.

Each sampling point runs once in Numba mode.
Set `python_mode: true` in a case's `task.yaml` entry to also run Python mode, or `python_mode: false` for Numba only.
When omitted, `python_mode` defaults to `true`.
Every run uses `--no-tally_output`, retaining standard metadata, runtime details, and the `performance/` group without saving tally results.
Output names encode the mode and particle count, for example `output_numba_10000.h5`.
Numba caching remains disabled so every Numba measurement includes compilation.
Cluster execution requests one process on one exclusive node.
HPC runs use the shared platform settings in `configs/platform_config.py` and user-specific account, queue, reservation, and Python paths in `configs/user_config.py`.
The C5G7 input uses the shared cross sections in `data/MGXS-C5G7.h5`.

## Launching and processing

From this suite directory, launch locally:

```console
python launch.py
```

Launch on a supported cluster:

```console
python launch.py --platform dane --walltime 1.0
```

Completed mode and particle-count outputs are skipped on relaunch, and case completion requires only the enabled modes.
Run `python process.py` after the jobs finish.
Pass a `maestro_run_<timestamp>` directory to process a specific launch.

For each case, processing creates `records.csv` and five log-log plots against total histories, $N$.
The plots are `runtime.png`, `tracking_rate.png`, `precision.png`, `precision_rate.png`, and `fom.png`.
The runtime is the total MC/DC runtime, including Numba compilation.
The tracking rate is the number of histories divided by total runtime.
MC/DC stores effective variance $V$ using fractional relative errors; the plots and derived CSV metrics use $V_{\%} = 10^4 V$ in percent squared.
With total runtime $T$, precision is $1/V_{\%}$ in $\%^{-2}$, precision rate is $1/(V_{\%}N)$ in $\%^{-2}$ per history, and figure of merit (FOM) is $1/(TV_{\%})$ in $\%^{-2}$ per second.
FOM is the product of tracking rate and precision rate: $(N/T)\,[1/(V_{\%}N)] = 1/(TV_{\%})$.
Runtime and history count come from `performance/runtime` and `performance/N_history`.
Effective variance comes from `performance/effective_variance`.
The CSV records all derived metrics, `performance/N_rank`, and the unchanged fractional effective variance for each execution mode.
Nonfinite or nonpositive effective variances are reported and their derived precision, precision-rate, and FOM values are recorded as `nan` and omitted from the plots.
If a metric has no finite positive values, its plot displays an explanatory message instead of a curve.
When Python mode is enabled, paired outputs must have matching history and batch counts and exactly one MPI rank.
Numba-only cases do not require Python outputs and omit Python columns and curves from the results.
The Numba compilation time is estimated as the median of the three smallest-history Numba runtimes.
The compilation-adjusted Numba series subtracts that estimate from each Numba runtime.
Runtime, tracking-rate, and FOM plots include this adjusted series; precision and precision rate do not depend on runtime.
Nonpositive compilation-adjusted runtimes and their derived tracking rates and FOM values are recorded as `nan` and omitted from the plots.
Numba uses a solid blue line with hollow circles, Python uses a dashed vermilion line with crosses, and compilation-adjusted Numba uses a dotted dark-purple line.

Run `python cleanup.py` to remove generated outputs, Maestro records, processed results, and `study.yaml`.
The study file is untracked and regenerated by `launch.py` for the selected platform.
Older runtime-only outputs lack the required metrics and must be moved aside or removed before relaunching, since existing outputs are skipped.

## Cases

| Case | Description |
| :--- | :---------- |
| [`c5g7-4phase`](cases/c5g7-4phase/) | Four-phase C5G7 transient problem. |
| [`kobayashi`](cases/kobayashi/) | Time-dependent Kobayashi dog-leg problem. |
