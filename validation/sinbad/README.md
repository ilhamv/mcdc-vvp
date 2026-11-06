# SINBAD Validation

Run and process experimental comparisons using locally available licensed SINBAD packages.
See the [complete SINBAD workflow](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/sinbad.html) and [benchmark descriptions and limitations](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/index.html).

## Inputs and configuration

The executable campaign contains [OKTAVIAN Si-60 neutron leakage](oktavian-si-60/README.md) and [FNG/TUD SiC neutron spectra](fng-tud-sic/README.md), with five configured cases in total. Each case has `input.py` and `plot.py`.
[FNG SiC response models](fng-sic/README.md) and [RFNC photon models](rfnc-photon-compounds/README.md) require additional response or coupled-particle capabilities and are not enabled comparisons.

Configure `task.yaml` as a benchmark/case mapping:

```yaml
oktavian-si-60:
  neutron_leakage:
    N_particle: 1_000_000_000
    walltime_factor: 0.34
fng-tud-sic:
  p1:
    N_particle: 1_000_000_000
    walltime_factor: 0.01
```

This is an excerpt; the supplied file also configures `p2`, `p3`, and `p4`. `N_particle` is particles per batch; batch count is set in each input.
Only enable cases that calculate the benchmark observable directly.
The transport environment needs MC/DC's native nuclear-data library. Official SINBAD packages are required when processing experimental comparisons and are not redistributed here.

## Launch and resume

From this suite, choose local execution:

```bash
python launch.py
```

Or run on the configured cluster:

```bash
python launch.py --platform dane --N_node 10 --walltime 24
```

Each case uses the selected nodes and configured CPU cores. Walltime in hours is scaled by the case factor, rounded up to scheduler resolution, and capped at the platform maximum. Local execution requires one node and ignores walltime.
Supplied factors were calibrated for ten-node Dane runs; recalibrate for different workloads/platforms.
Existing `output_<N_particle>.h5` files are skipped. Preserve old outputs separately before changing inputs.
Shared platform and account/interpreter settings come from `configs/`.

## Process

After jobs finish, provide the root containing the local SINBAD repositories:

```bash
python process.py /path/to/sinbad
```

Or select a particular saved study:

```bash
python process.py /path/to/sinbad maestro_run_<timestamp>
```

The processor resolves official packages, invokes case plotters, and collects figures under `results/<benchmark>/<case>/`, retaining launch/task metadata.
For repository-wide processing, register this suite in `configs/launch_config.py` and set its `sinbad_root` to the local package root.

## Cleanup

After jobs stop, `python cleanup.py` removes outputs/figures for configured cases, processed results, Maestro directories, and `study.yaml`. Inputs, reference packages, and model inputs outside `task.yaml` are retained.
