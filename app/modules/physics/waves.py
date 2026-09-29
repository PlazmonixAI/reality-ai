"""Waves: a driven string (finite-difference wave equation) and multi-slit interference / diffraction."""
import math

import numpy as np

from app.core.registry import tool

MAX_CELLS = 2_000
MAX_FRAMES = 1_000


@tool(
    domain="physics",
    name="string_wave",
    description=(
        "Wave on a string: numerically solves the damped wave equation u_tt = c^2 u_xx - gamma u_t with the left "
        "end driven. driver: 'oscillate' (A sin 2 pi f t) or 'pulse' (one smooth pulse of the given width in s). "
        "end: 'fixed', 'loose' or 'none' (no reflection). c = sqrt(tension / linear_density). Returns wave speed, "
        "wavelength, harmonic frequencies and plot-ready frames u(x, t). Example: length=2, tension=10, "
        "linear_density=0.01, frequency=15, amplitude=0.02, end='fixed', duration=1."
    ),
)
def string_wave(
    length: float,
    tension: float,
    linear_density: float,
    duration: float,
    driver: str = "oscillate",
    frequency: float = 5.0,
    amplitude: float = 0.01,
    pulse_width: float = 0.05,
    damping: float = 0.0,
    end: str = "fixed",
    n_cells: int = 200,
    n_frames: int = 200,
) -> dict:
    if min(length, tension, linear_density, duration) <= 0:
        raise ValueError("length, tension, linear_density and duration must be positive")
    if driver not in ("oscillate", "pulse"):
        raise ValueError("driver must be 'oscillate' or 'pulse'")
    if end not in ("fixed", "loose", "none"):
        raise ValueError("end must be 'fixed', 'loose' or 'none'")
    if frequency <= 0 or pulse_width <= 0 or damping < 0:
        raise ValueError("frequency and pulse_width must be positive, damping >= 0")
    if not 10 <= n_cells <= MAX_CELLS or not 2 <= n_frames <= MAX_FRAMES:
        raise ValueError(f"n_cells must be 10..{MAX_CELLS} and n_frames 2..{MAX_FRAMES}")

    c = math.sqrt(tension / linear_density)
    dx = length / n_cells
    dt = dx / c                       # Courant number 1: exact propagation for the undamped scheme
    steps = int(math.ceil(duration / dt))
    if steps > 400_000:
        raise ValueError("Too many time steps; shorten duration or use fewer cells")

    def drive(t: float) -> float:
        if driver == "oscillate":
            return amplitude * math.sin(2 * math.pi * frequency * t)
        t0 = 2 * pulse_width
        return amplitude * math.exp(-(((t - t0) / (pulse_width / 2)) ** 2)) if t < 2 * t0 else 0.0

    x = np.linspace(0, length, n_cells + 1)
    u_prev, u = np.zeros_like(x), np.zeros_like(x)
    g = damping * dt / 2
    mur = 0.0                         # (r - 1) / (r + 1) with r = 1
    frame_times = np.linspace(0, steps * dt, n_frames)
    frames, k = [], 0
    for n in range(steps + 1):
        t = n * dt
        while k < n_frames and frame_times[k] <= t + 1e-12:
            frames.append(u.copy()); k += 1
        if n == steps:
            break
        u_next = np.empty_like(u)
        u_next[1:-1] = (2 * u[1:-1] - (1 - g) * u_prev[1:-1] + (u[2:] - 2 * u[1:-1] + u[:-2])) / (1 + g)
        u_next[0] = drive(t + dt)
        if end == "fixed":
            u_next[-1] = 0.0
        elif end == "loose":
            # Free end (u_x = 0): mirror ghost point, u[N+1] = u[N-1]
            u_next[-1] = (2 * u[-1] - (1 - g) * u_prev[-1] + 2 * (u[-2] - u[-1])) / (1 + g)
        else:
            u_next[-1] = u[-2] + mur * (u_next[-2] - u[-1])
        u_prev, u = u, u_next
    while len(frames) < n_frames:
        frames.append(u.copy())

    wavelength = c / frequency if driver == "oscillate" else None
    ends = "fixed-fixed" if end == "fixed" else "fixed-free" if end == "loose" else None
    if ends == "fixed-fixed":
        harmonics = [n * c / (2 * length) for n in range(1, 6)]
    elif ends == "fixed-free":
        harmonics = [(2 * n - 1) * c / (4 * length) for n in range(1, 6)]
    else:
        harmonics = []
    return {
        "result": {
            "wave_speed": c,
            "wavelength": wavelength,
            "period": 1 / frequency if driver == "oscillate" else None,
            "travel_time": length / c,
            "harmonics": harmonics,
        },
        "frames": {"x": x.tolist(), "t": frame_times.tolist(), "u": [f.tolist() for f in frames]},
        "units": "lengths m, speed m/s, frequency Hz, time s, displacement m",
        "assumptions": [
            "Small-amplitude linear wave equation, uniform string, linear damping",
            "Left end is driven (clamped to the driver); finite differences at Courant number 1",
            {"fixed": "Right end fixed (u = 0)", "loose": "Right end free to slide (u_x = 0)",
             "none": "Right end absorbing (no reflection)"}[end],
        ],
    }


@tool(
    domain="physics",
    name="slit_interference",
    description=(
        "Fraunhofer interference / diffraction from N identical slits (N=1 single slit, N=2 double slit, larger "
        "N a grating). wavelength, slit_width, slit_spacing and screen_distance in metres. Returns the intensity "
        "pattern on the screen, maxima/minima positions and the complex 2D wave field near the slits for "
        "animation. Example: wavelength=650e-9, n_slits=2, slit_width=20e-6, slit_spacing=100e-6, screen_distance=1."
    ),
)
def slit_interference(
    wavelength: float,
    slit_spacing: float,
    screen_distance: float,
    n_slits: int = 2,
    slit_width: float = 0.0,
    screen_half_width: float | None = None,
    n_points: int = 1001,
) -> dict:
    if wavelength <= 0 or screen_distance <= 0 or slit_width < 0:
        raise ValueError("wavelength and screen_distance must be positive, slit_width >= 0")
    if not 1 <= n_slits <= 100:
        raise ValueError("n_slits must be between 1 and 100")
    if n_slits > 1 and slit_spacing <= slit_width:
        raise ValueError("slit_spacing must be larger than slit_width")
    if n_slits == 1 and slit_width == 0:
        raise ValueError("A single slit needs a slit_width > 0")
    if not 11 <= n_points <= 20_001:
        raise ValueError("n_points must be between 11 and 20001")

    d, a, lam, D, N = slit_spacing, slit_width, wavelength, screen_distance, n_slits
    if screen_half_width is None:
        scale = lam / (a if N == 1 else d)
        screen_half_width = D * math.tan(min(math.asin(min(1.0, 3.5 * scale)), math.radians(80)))
    y = np.linspace(-screen_half_width, screen_half_width, n_points)
    theta = np.arctan2(y, D)
    s = np.sin(theta)
    beta = np.pi * a * s / lam
    envelope = np.sinc(beta / np.pi) ** 2 if a > 0 else np.ones_like(s)
    if N > 1:
        alpha = np.pi * d * s / lam
        with np.errstate(divide="ignore", invalid="ignore"):
            grating = (np.sin(N * alpha) / (N * np.sin(alpha))) ** 2
        grating = np.where(np.abs(np.sin(alpha)) < 1e-12, 1.0, grating)
    else:
        grating = np.ones_like(s)
    intensity = envelope * grating

    def positions(step: float, offset: float = 0.0, limit: int = 12) -> list[float]:
        out = []
        for m in range(-limit, limit + 1):
            v = (m + offset) * step
            if abs(v) < 1 and abs(D * math.tan(math.asin(v))) <= screen_half_width:
                out.append(D * math.tan(math.asin(v)))
        return sorted(out)

    maxima = positions(lam / d) if N > 1 else [0.0]
    if N > 1:
        minima = positions(lam / d, 0.5) if N == 2 else []
    else:
        minima = [p for p in positions(lam / a) if abs(p) > 0]

    # Complex 2D field near the slits (Huygens sum of cylindrical waves) for animation, sampled at
    # >= 5 points per wavelength. If the slits are too far apart to draw that finely, the spacing is
    # compressed for this view only (flagged); the screen pattern above is always exact.
    k = 2 * math.pi / lam
    max_waves = 36.0
    d_view = d if N == 1 or d * (N - 1) / lam <= max_waves - 12 else (max_waves - 12) * lam / (N - 1)
    compressed = d_view != d
    span_y = (d_view * (N - 1) if N > 1 else 0) + 12 * lam
    span_x = 1.2 * span_y
    gy = int(min(200, max(60, math.ceil(5 * span_y / lam))))
    gx = int(min(240, max(80, math.ceil(5 * span_x / lam))))
    xs = np.linspace(lam * 0.5, span_x, gx)
    ys = np.linspace(-span_y / 2, span_y / 2, gy)
    X, Y = np.meshgrid(xs, ys)
    field = np.zeros_like(X, dtype=complex)
    centres = (np.arange(N) - (N - 1) / 2) * d_view
    for yc in centres:
        r = np.hypot(X, Y - yc)
        field += np.exp(1j * k * r) / np.sqrt(k * r)
    field /= np.max(np.abs(field))
    return {
        "result": {
            "fringe_spacing": lam * D / d if N > 1 else None,
            "central_width": 2 * lam * D / a if a > 0 else None,
            "maxima": maxima,
            "minima": minima,
        },
        "pattern": {"y": y.tolist(), "intensity": intensity.tolist()},
        "near_field": {"x": xs.tolist(), "y": ys.tolist(), "re": field.real.round(4).tolist(),
                       "im": field.imag.round(4).tolist(), "slits_y": centres.tolist(),
                       "spacing_compressed": compressed},
        "units": "positions m, intensity relative to the central maximum",
        "assumptions": [
            "Fraunhofer (far-field) intensity: sinc^2 single-slit envelope x N-slit grating factor",
            "Monochromatic plane wave at normal incidence; scalar waves",
            "Near field: Huygens sum of cylindrical waves from point-like slits (for visualisation)",
        ],
    }
