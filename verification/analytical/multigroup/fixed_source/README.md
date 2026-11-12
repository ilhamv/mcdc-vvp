# Analytical Multigroup Fixed-Source Verification

The [suite guide](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/analytical/multigroup/fixed_source/index.html) describes the fixed-source cases and how their MC/DC results compare with analytical solutions.

## Quick run

From this suite directory, set [task.yaml](task.yaml) to run the Absorbium slab at three particle counts between 1,000 and 10,000.

```yaml
slab_absorbium:
  logN_min: 3
  logN_max: 4
  N_task: 3
```

Launch the local study.

```bash
python launch.py
```

After the study finishes, run `python process.py` to write convergence and comparison plots under `results/`.
See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for platform runs and processing options.
