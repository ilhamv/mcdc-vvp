# Code-to-Code Multigroup Fixed-Source Verification

The [suite guide](https://mcdc.readthedocs.io/en/dev/project/vvp/verification/code_to_code/multigroup/fixed_source/index.html) describes the C5G7 and Kobayashi comparisons between MC/DC and OpenMC.

## Quick run

From this suite directory, keep only the `c5g7-4phase` entry in [task.yaml](task.yaml) for a C5G7 run.
Keep its five particle counts and the case input’s 30 batches to match the OpenMC reference data.

Download the C5G7 reference files and launch on a [configured platform](../../../../README.md#quick-run-on-a-platform) such as Dane.

```bash
python cases/c5g7-4phase/reference.py
python launch.py --platform dane
```

After the study finishes, run `python process.py` to write convergence and comparison plots and animations under `results/`.

For baseline Kobayashi, download its references with `python cases/kobayashi/reference.py`.
The detector case requires separate detector-capture reference files.
See [Verification Workflows](https://mcdc.readthedocs.io/en/dev/project/vvp/campaigns/verification.html) for reference data and processing options.
