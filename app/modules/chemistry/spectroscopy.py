"""Beer-Lambert law and absorbance spectra built from absorption bands."""
import math
from typing import Any

import numpy as np

from app.core.registry import tool


@tool(
    domain="chemistry",
    name="beer_lambert",
    description=(
        "Beer-Lambert law A = epsilon l c, T = 10^-A. Give molar absorptivity (L mol^-1 cm^-1) and path length (cm) "
        "plus exactly one of concentration (mol/L), absorbance or transmittance (0..1); the others are solved. "
        "Example: absorptivity=2400, path_length=1, concentration=2e-4."
    ),
)
def beer_lambert(
    absorptivity: float,
    path_length: float,
    concentration: float | None = None,
    absorbance: float | None = None,
    transmittance: float | None = None,
) -> dict:
    if absorptivity <= 0 or path_length <= 0:
        raise ValueError("absorptivity and path_length must be positive")
    given = [v is not None for v in (concentration, absorbance, transmittance)]
    if sum(given) != 1:
        raise ValueError("Give exactly one of concentration, absorbance or transmittance")
    if concentration is not None:
        if concentration < 0:
            raise ValueError("concentration must be >= 0")
        a = absorptivity * path_length * concentration
    elif absorbance is not None:
        if absorbance < 0:
            raise ValueError("absorbance must be >= 0")
        a = absorbance
    else:
        if not 0 < transmittance <= 1:
            raise ValueError("transmittance must be in (0, 1]")
        a = -math.log10(transmittance)
    c = a / (absorptivity * path_length)
    return {
        "result": {"absorbance": a, "transmittance": 10 ** -a, "concentration": c},
        "percent_transmitted": 100 * 10 ** -a,
        "units": "absorbance dimensionless, transmittance fraction, concentration mol/L",
        "assumptions": ["Monochromatic light, dilute solution, no scattering (Beer-Lambert regime)"],
    }


@tool(
    domain="chemistry",
    name="absorbance_spectrum",
    description=(
        "Absorbance and transmittance spectrum of a solution whose molar absorptivity is a sum of Gaussian "
        "bands [{wavelength (nm), epsilon (L/mol/cm), width (nm, standard deviation)}], at a concentration "
        "(mol/L) and path length (cm). Optionally reports values at one probe wavelength. "
        "Example: bands=[{wavelength:525,epsilon:2400,width:25}], concentration=1e-4, path_length=1, probe=525."
    ),
)
def absorbance_spectrum(
    bands: list[dict[str, Any]],
    concentration: float,
    path_length: float = 1.0,
    probe: float | None = None,
    wl_min: float = 380.0,
    wl_max: float = 780.0,
    n_points: int = 401,
) -> dict:
    if not 1 <= len(bands) <= 10:
        raise ValueError("Give 1..10 absorption bands")
    if concentration < 0 or path_length <= 0 or not 0 < wl_min < wl_max:
        raise ValueError("concentration >= 0, path_length > 0 and 0 < wl_min < wl_max required")
    wl = np.linspace(wl_min, wl_max, n_points)

    def eps(x):
        total = np.zeros_like(np.asarray(x, dtype=float))
        for b in bands:
            w, e, s = float(b["wavelength"]), float(b["epsilon"]), float(b["width"])
            if e < 0 or s <= 0:
                raise ValueError("Band epsilon must be >= 0 and width > 0")
            total = total + e * np.exp(-0.5 * ((x - w) / s) ** 2)
        return total

    e = eps(wl)
    a = e * path_length * concentration
    k = int(np.argmax(e))
    out = {"lambda_max": float(wl[k]), "epsilon_max": float(e[k])}
    if probe is not None:
        ep = float(eps(np.array(probe)))
        ap = ep * path_length * concentration
        out.update({"probe_wavelength": probe, "probe_epsilon": ep, "probe_absorbance": ap, "probe_transmittance": 10 ** -ap})
    return {
        "result": out,
        "spectrum": {"wavelength": wl.tolist(), "epsilon": e.tolist(), "absorbance": a.tolist(), "transmittance": (10 ** -a).tolist()},
        "units": "wavelength nm, epsilon L mol^-1 cm^-1, absorbance dimensionless, transmittance fraction",
        "assumptions": ["Absorption bands modelled as Gaussians in wavelength", "Beer-Lambert law at each wavelength"],
    }
