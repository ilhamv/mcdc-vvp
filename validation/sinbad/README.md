# SINBAD Validation

Compare MC/DC neutron spectra with measurements from [OKTAVIAN Si-60](oktavian-si-60/README.md) and [FNG/TUD SiC](fng-tud-sic/README.md).
The [SINBAD workflow guide](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/sinbad.html) covers case selection, experimental data, and processing.

## Quick run

Set `MCDC_LIB` to the directory containing MC/DC’s native nuclear-data library.
From this suite directory, launch the cases in [task.yaml](task.yaml) on a [configured platform](../../README.md#quick-run-on-a-platform) such as Dane.

```bash
python launch.py --platform dane
```

After the study finishes, pass the directory containing your licensed SINBAD packages to the processor.

```bash
python process.py /path/to/sinbad
```

Find the comparison plots in `results/<benchmark>/<case>/`.
