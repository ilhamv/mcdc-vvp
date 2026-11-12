# RFNC Compound Photon Spectra

The [benchmark documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/rfnc_photon_compounds.html) contains the experiment, geometry figures, computational assumptions, uncertainties, limitations, and references.

## Inputs and supported outputs

This model is not enabled in the executable SINBAD suite.
`input.py` defines the experiment geometry and prescribed source, then raises `NotImplementedError` because neutron-induced photon production and transport are required for the benchmark observable.
`plot.py` displays experimental photon spectra only; it does not compare an MC/DC output.

## Use and processing

Obtain the licensed package locally.
From this directory, plot its experimental tables with:

```bash
python plot.py /path/to/package/01_Experiment_Input
```

The input directory must contain `tab2res.txt`.
The displayed 12% combined experimental uncertainty is not identified as a one-standard-deviation interval.
Consult Sphinx for sample selection, model assumptions, and requirements for a complete comparison.

The plot is saved as `experimental-photon-spectra.png` in the working directory.

For model inspection, `input.py` requires one sample argument: `h2o-sphere`, `sio2-sphere`, `sio2-back-hemisphere`, `nacl-sphere`, or `nacl-back-hemisphere`.
It stops with the stated capability error after model construction; it does not generate a transport result.
