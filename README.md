# MC/DC-VVP

![MC/DC logo](https://raw.githubusercontent.com/mcdc-project/mcdc/main/assets/mcdc-logo.svg)

Run verification, validation, and performance campaigns for [MC/DC](https://github.com/mcdc-project/mcdc), orchestrated with [Maestro](https://github.com/LLNL/maestrowf).

## Quick local example

Start in this repository root with an MC/DC environment and the [campaign dependencies](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/setup.html) installed.

For a small fixed-source demonstration, set `configs/launch_config.py` to:

```python
LAUNCH_CONFIG = {
    "verification/analytical/multigroup/fixed_source": {
        "enabled": True,
        "platforms": ["local"],
        "N_node": 1,
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

Find the plots and saved configuration in `results/verification/analytical/multigroup/fixed_source/`. Use `python prepare_release.py` to prepare the PNG/GIF assets in `release/`.

## Documentation

- [Operating campaigns](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/index.html): setup, HPC execution, resuming, processing, cleanup, and publication.
- [VVP overview and suites](https://mcdc.readthedocs.io/en/dev/project/vvp/index.html): verification, validation, performance, and their evidence.
- [Contributing cases and suites](https://mcdc.readthedocs.io/en/dev/project/vvp/contributing.html).
