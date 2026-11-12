# Analytical Multigroup k-Eigenvalue Verification

The [suite guide](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/analytical/multigroup/k_eigenvalue/index.html) describes the analytical multiplication factors and flux shapes used to verify MC/DC.

## Quick run

From this suite directory, set [task.yaml](task.yaml) to run the one-group slab with 5, 10, and 20 active cycles.
The [case input](cases/one_group_slab/input.py) sets the particles per cycle and the number of inactive cycles.

```yaml
one_group_slab:
  N_active_min: 5
  N_active_max: 20
  N_task: 3
```

Launch the local study.

```bash
python launch.py
```

After the study finishes, run `python process.py` to write convergence plots, flux shapes, and cycle histories under `results/`.
See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for platform runs and processing options.
