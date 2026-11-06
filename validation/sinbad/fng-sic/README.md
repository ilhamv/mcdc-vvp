# FNG SiC Response Models

The [benchmark documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/validation/fng_sic.html) contains the experiment, geometry figures, computational assumptions, uncertainties, limitations, and references.

## Inputs and supported outputs

These inputs are not enabled in the executable SINBAD suite:

- `activation/` produces neutron spectra for response folding. Final benchmark reaction rates require the prescribed IRDF response functions.
- `tld/` produces neutron spectra in the dosimeter volumes. Total absorbed dose additionally requires neutron-response weighting and photon energy deposition.

Their plots are intermediate spectra, not final experimental C/E comparisons. Do not add them to `task.yaml` as completed benchmark observables.

## Use and processing

Inputs require the native nuclear-data library. To inspect an existing output, run from `activation/` or `tld/`:

```bash
python plot.py output.h5
```

The plotters take one output path and do not read experimental packages. Consult Sphinx for response requirements and model assumptions before extending either input.

The plotters save `neutron-spectra.png` in the working directory.
