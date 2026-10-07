"""Compare the detector-explicit MC/DC Si-60 result with SINBAD Table 3."""

import argparse
import os
from pathlib import Path
import re

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FLOAT_PATTERN = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
SINBAD_INPUTS_ENV = "SINBAD_OKTAVIAN_INPUTS"
DETECTOR_CENTER_DISTANCE_CM = 1097.45


def find_sinbad_inputs(configured=None):
    """Locate the licensed directory containing oksi-exp.md."""
    if configured is None:
        configured = os.environ.get(SINBAD_INPUTS_ENV)
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"SINBAD input directory not found: {candidate}")

    project_root = Path(__file__).resolve().parents[4]
    candidates = sorted(project_root.glob("sinbad/*oktav_si*/00_Report/10_Inputs"))
    if len(candidates) == 1:
        return candidates[0]
    raise FileNotFoundError(
        "Pass --sinbad-inputs or set SINBAD_OKTAVIAN_INPUTS to the official "
        "benchmark's 00_Report/10_Inputs directory."
    )


def read_experiment(path):
    """Read the 60 cm neutron leakage rows from SINBAD Table 3."""
    lines = path.read_text().splitlines()
    heading_index = next(
        (index for index, line in enumerate(lines) if line.startswith("### Table 3")),
        None,
    )
    if heading_index is None:
        raise ValueError(f"Could not find Table 3 in {path}")

    rows = []
    in_fence = False
    for line in lines[heading_index + 1 :]:
        if line.strip().startswith("```"):
            if in_fence:
                break
            in_fence = True
            continue
        if not in_fence:
            continue
        values = FLOAT_PATTERN.findall(line)
        if len(values) == 4:
            rows.append(tuple(float(value) for value in values))
    if not rows:
        raise ValueError(f"No Table 3 data found in {path}")
    return np.asarray(sorted(rows))


parser = argparse.ArgumentParser()
parser.add_argument("input", nargs="?", default="output.h5")
parser.add_argument("--output", default="neutron-leakage.png")
parser.add_argument("--sinbad-inputs")
parser.add_argument(
    "--normalization-uncertainty",
    type=float,
    default=0.0,
    help="Optional relative source-normalization uncertainty; the package gives "
    "a 0.004-0.01 range but no single value or covariance.",
)
parser.add_argument(
    "--minimum-benchmark-energy",
    type=float,
    default=3.0,
    help="Shade the lower-energy region requiring additional background details.",
)
args = parser.parse_args()

if args.normalization_uncertainty < 0.0:
    parser.error("--normalization-uncertainty must be nonnegative")

sinbad_inputs = find_sinbad_inputs(args.sinbad_inputs)
experiment = read_experiment(sinbad_inputs / "oksi-exp.md")
exp_lower, exp_upper, exp_spectrum, exp_stat_sdev = experiment.T
exp_energy = np.sqrt(exp_lower * exp_upper)

with h5py.File(args.input, "r") as output:
    tally = output["tallies/neutron_detector_flux_energy"]
    energy_edges = tally["grid/energy"][:] * 1.0e-6
    detector_flux = np.asarray(tally["flux/mean"][:]).squeeze()
    detector_flux_sdev = np.asarray(tally["flux/sdev"][:]).squeeze()

expected_edges = np.concatenate((exp_lower, exp_upper[-1:]))
if len(energy_edges) != len(expected_edges) or not np.allclose(
    energy_edges, expected_edges, rtol=2.0e-3, atol=0.0
):
    raise ValueError("MC/DC tally grid does not match SINBAD Table 3")

energy = np.sqrt(energy_edges[:-1] * energy_edges[1:])
lethargy_width = np.log(energy_edges[1:] / energy_edges[:-1])
# Convert the far-field cell flux [cm^-2/source] to the total-equivalent
# leakage used by the experimental table.  This 4*pi*R^2 interpretation is the
# scalar-leakage approximation described in the benchmark assessment.
geometric_factor = 4.0 * np.pi * DETECTOR_CENTER_DISTANCE_CM**2
calculated = detector_flux * geometric_factor / lethargy_width
calculated_sdev = detector_flux_sdev * geometric_factor / lethargy_width

# The optional normalization contribution is pointwise-combined only for display.
# It remains fully correlated and does not supply the missing covariance matrix.
exp_sdev = np.hypot(exp_stat_sdev, args.normalization_uncertainty * exp_spectrum)
ratio = np.divide(
    calculated,
    exp_spectrum,
    out=np.full_like(calculated, np.nan),
    where=exp_spectrum > 0.0,
)
relative_calculated = np.divide(
    calculated_sdev,
    calculated,
    out=np.zeros_like(calculated_sdev),
    where=calculated > 0.0,
)
relative_experiment = np.divide(
    exp_sdev,
    exp_spectrum,
    out=np.zeros_like(exp_sdev),
    where=exp_spectrum > 0.0,
)
ratio_sdev = ratio * np.hypot(relative_calculated, relative_experiment)

figure, (spectrum_axis, ratio_axis) = plt.subplots(
    2,
    1,
    figsize=(7.2, 6.8),
    sharex=True,
    gridspec_kw={"height_ratios": [2.2, 1.0]},
)
spectrum_axis.errorbar(
    exp_energy,
    exp_spectrum,
    xerr=np.vstack((exp_energy - exp_lower, exp_upper - exp_energy)),
    yerr=exp_sdev,
    fmt="o",
    markersize=3.0,
    color="black",
    ecolor="0.45",
    elinewidth=0.7,
    capsize=0.0,
    label="Experiment (pointwise 1σ)",
)
spectrum_axis.step(
    energy, calculated, where="mid", color="tab:blue", linewidth=1.4, label="MC/DC"
)
spectrum_axis.fill_between(
    energy,
    np.maximum(calculated - calculated_sdev, np.finfo(float).tiny),
    calculated + calculated_sdev,
    step="mid",
    color="tab:blue",
    alpha=0.22,
    linewidth=0.0,
    label="MC standard error",
)
spectrum_axis.set_yscale("log")
spectrum_axis.set_ylabel("Leakage per unit lethargy\n[source neutron]$^{-1}$")
spectrum_axis.set_title("OKTAVIAN Si-60 — detector-explicit 3-D model")
spectrum_axis.legend(fontsize="small")

ratio_axis.errorbar(
    energy,
    ratio,
    yerr=ratio_sdev,
    fmt="o",
    markersize=2.8,
    color="tab:blue",
    ecolor="tab:blue",
    elinewidth=0.7,
)
ratio_axis.axhline(1.0, color="black", linewidth=0.9)
ratio_axis.set_ylabel("C/E")
ratio_axis.set_xlabel("Neutron energy [MeV]")

for axis in (spectrum_axis, ratio_axis):
    axis.axvspan(
        energy_edges[0],
        args.minimum_benchmark_energy,
        color="0.90",
        zorder=-10,
    )
    axis.grid(which="both", alpha=0.22)
spectrum_axis.text(
    0.02,
    0.03,
    "Shaded: incomplete background specification below 3 MeV",
    transform=spectrum_axis.transAxes,
    fontsize="small",
    color="0.30",
)
ratio_axis.set_xscale("log")
ratio_axis.set_xlim(energy_edges[0], energy_edges[-1])

figure.tight_layout()
figure.savefig(args.output, dpi=200)
plt.close(figure)
