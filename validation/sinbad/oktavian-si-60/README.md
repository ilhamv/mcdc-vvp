# OKTAVIAN Si-60

The [benchmark documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/oktavian_si60.html) contains the experiment, geometry figures, computational assumptions, uncertainties, limitations, and references.

## Inputs and supported outputs

- `neutron_leakage/` calculates the neutron-spectrum observable and is enabled in the suite's task configuration.
- `gamma_leakage/` defines the gamma experiment model, but its input stops explicitly because coupled photon production/transport is required. Its plotter displays experimental data only.

The neutron comparison uses published bins from 3.0288 to 13.574 MeV. Use the supplied tally grid and normalization when processing; see Sphinx for the range justification and model approximations.

## Use and processing

Use the suite launcher and processor from `validation/sinbad`; see the [suite README](../README.md). For direct plotting, run from `neutron_leakage/`:

```bash
python plot.py output_<N_particle>.h5 /path/to/package/01_Experiment_Input
```

The package input directory must contain `oksi-exp.md`. In `gamma_leakage/`, `python plot.py /path/to/package/01_Experiment_Input` plots the experimental photon spectrum without a simulated comparison.

The neutron plot is saved as `neutron_leakage.png` in the working directory.
