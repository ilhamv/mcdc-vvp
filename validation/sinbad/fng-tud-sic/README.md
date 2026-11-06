# FNG/TUD SiC Spectra

The [benchmark documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/fng_tud_sic.html) contains the experiment, geometry figures, computational assumptions, uncertainties, limitations, and references.

## Inputs and supported outputs

`p1/`, `p2/`, `p3/`, and `p4/` are separate detector-depth inputs enabled in the suite's task configuration. Each supplies `input.py` and `plot.py`.
The neutron comparison uses published bins from 0.999 to 15.22 MeV. The simultaneously measured photon observable requires coupled photon production and transport.

## Use and processing

Use the suite launcher and processor from `validation/sinbad`; see the [suite README](../README.md). To plot a selected neutron output, run from its `p1/`--`p4/` directory:

```bash
python plot.py output_<N_particle>.h5 /path/to/package/01_Experiment_Input
```

The package input directory must contain `tudsic-e.md`. Retain the supplied tally bins and normalization so they match the experimental tables.

Each case plot is saved as `neutron_spectrum.png` in the working directory.
