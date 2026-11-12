# MC/DC-VVP

![MC/DC logo](https://raw.githubusercontent.com/mcdc-project/mcdc/main/assets/mcdc-logo.svg)

MC/DC-VVP organizes and runs verification, validation, and performance campaigns for [MC/DC](https://github.com/mcdc-project/mcdc), orchestrated with [Maestro](https://github.com/LLNL/maestrowf).

The MC/DC documentation describes the VVP suites and how to run campaigns or contribute new cases.

- [VVP overview and suites](https://mcdc.readthedocs.io/en/dev/project/vvp/index.html): verification, validation, performance, and their evidence.
- [Operating campaigns](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/index.html): setup, HPC execution, resuming, processing, cleanup, and publication.
- [Contributing cases and suites](https://mcdc.readthedocs.io/en/dev/project/vvp/contributing.html).

## Quick local example

Start in this repository root with an MC/DC environment and the [campaign dependencies](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/setup.html) installed.

On a fresh checkout, copy the launch and user configuration templates before editing your settings.

```bash
cp -n configs/launch_config.py.template configs/launch_config.py
cp -n configs/user_config.py.template configs/user_config.py
```

For a small fixed-source demonstration, set `configs/launch_config.py` to:

```python
LAUNCH_CONFIG = {
    "verification/analytical/multigroup/fixed_source": {
        "enabled": True,
    },
}
```

Set `verification/analytical/multigroup/fixed_source/task.yaml` to:

```yaml
slab_absorbium:
  logN_min: 3
  logN_max: 4
  N_task: 3
```

Launch the three sampling tasks:

```bash
python launch.py
```

After the Maestro study finishes, process and collect its results:

```bash
python process.py
```

Find the plots and saved configuration in `results/verification/analytical/multigroup/fixed_source/`.
Run `python prepare_release.py` to collect the PNG figures and GIF animations in `release/`.
These files are ready to attach to an MC/DC release, where the documentation links to them directly.

## Quick run on a platform

On your chosen platform, activate your MC/DC environment and enable the fixed-source suite in `configs/launch_config.py` as in the [quick local example](#quick-local-example).
Check for your platform in the `PLATFORMS` dictionary in [configs/platform_config.py](configs/platform_config.py).
If it is missing, copy an entry for a system with the same scheduler, give it your platform’s name, and update the host, launch commands, node resources, and job limits to match your system.
Use that same platform name in `configs/user_config.py` and with `--platform`.
For example, a Dane user with access to the `pbatch` queue could use the following settings.

```python
USER_CONFIG = {
    "dane": {"account": "your_account", "queue": "pbatch"},
}
```

For the same three sampling points, set `verification/analytical/multigroup/fixed_source/task.yaml` to request one node and 30 minutes for the case.

```yaml
slab_absorbium:
  logN_min: 3
  logN_max: 4
  N_task: 3
  N_node: 1
  walltime: 0.5  # Hours for the whole case.
```

From the repository root, launch with your platform name (shown here for Dane).

```bash
python launch.py --platform dane
```
