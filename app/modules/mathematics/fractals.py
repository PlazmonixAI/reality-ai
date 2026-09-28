"""Escape-time fractals: the Mandelbrot set and Julia sets, with smooth iteration counts."""
import base64

import numpy as np

from app.core.registry import tool

INSIDE = 65535  # uint16 marker for points that never escaped


def escape_time(z0: np.ndarray, c: np.ndarray, max_iter: int, radius: float = 256.0) -> np.ndarray:
    """Smooth escape count ν = n + 1 − log2(log|z_n|) for each point; NaN if it never escaped."""
    z = z0.astype(complex).copy()
    cc = np.broadcast_to(c, z.shape).astype(complex).copy()
    out = np.full(z.shape, np.nan)
    active = np.ones(z.shape, bool)
    idx = np.flatnonzero(active)
    zf, cf = z.ravel(), cc.ravel()
    r2 = radius * radius
    for n in range(max_iter):
        za = zf[idx]
        za = za * za + cf[idx]
        zf[idx] = za
        esc = (za.real * za.real + za.imag * za.imag) > r2
        if esc.any():
            e_idx = idx[esc]
            mod = np.abs(zf[e_idx])
            out.ravel()[e_idx] = n + 1 - np.log2(np.log(mod))
            idx = idx[~esc]
        if idx.size == 0:
            break
    return out


def in_mandelbrot(c: complex, max_iter: int = 1000) -> bool:
    z = 0j
    for _ in range(max_iter):
        z = z * z + c
        if abs(z) > 2:
            return False
    return True


@tool(
    domain="mathematics",
    name="fractal",
    description=(
        "Escape-time image of the Mandelbrot set (z → z² + c, z0 = 0, c = pixel) or a Julia set (z0 = pixel, "
        "fixed c = c_re + i c_im). View centred at (center_re, center_im) with the given width; returns smooth "
        "iteration counts as base64 little-endian uint16 (value/16, 65535 = inside), the fraction of pixels inside "
        "and an area estimate. Example: kind='mandelbrot', center_re=-0.75, width=3.5."
    ),
)
def fractal(
    kind: str = "mandelbrot",
    center_re: float = -0.75,
    center_im: float = 0.0,
    width: float = 3.5,
    pixels_x: int = 320,
    pixels_y: int = 240,
    max_iter: int = 200,
    c_re: float = -0.8,
    c_im: float = 0.156,
) -> dict:
    if kind not in ("mandelbrot", "julia"):
        raise ValueError("kind must be 'mandelbrot' or 'julia'")
    if not (16 <= pixels_x <= 1200 and 16 <= pixels_y <= 1200) or pixels_x * pixels_y > 640_000:
        raise ValueError("pixels_x and pixels_y must be 16..1200 with at most 640000 pixels")
    if not 10 <= max_iter <= 5000:
        raise ValueError("max_iter must be between 10 and 5000")
    if not 0 < width <= 20:
        raise ValueError("width must be between 0 and 20")
    height = width * pixels_y / pixels_x
    xs = center_re + (np.arange(pixels_x) + 0.5 - pixels_x / 2) * (width / pixels_x)
    ys = center_im - (np.arange(pixels_y) + 0.5 - pixels_y / 2) * (height / pixels_y)  # top row = largest Im
    grid = xs[None, :] + 1j * ys[:, None]
    if kind == "mandelbrot":
        nu = escape_time(np.zeros_like(grid), grid, max_iter)
        c_info = None
    else:
        c = complex(c_re, c_im)
        nu = escape_time(grid, np.full(grid.shape, c), max_iter)
        c_info = {"c": [c_re, c_im], "connected": in_mandelbrot(c)}
    inside = np.isnan(nu)
    enc = np.where(inside, INSIDE, np.clip(np.round(np.nan_to_num(nu, nan=0) * 16), 0, INSIDE - 1)).astype("<u2")
    frac = float(inside.mean())
    return {
        "result": {
            "kind": kind,
            "fraction_inside": frac,
            "area_inside": frac * width * height,
            "max_escape": float(np.nanmax(nu)) if (~inside).any() else None,
            "julia": c_info,
        },
        "image": {
            "width": pixels_x, "height": pixels_y, "encoding": "base64 uint16 little-endian, smooth count × 16, 65535 = inside",
            "data": base64.b64encode(enc.tobytes()).decode("ascii"),
            "re_range": [float(xs[0] - width / pixels_x / 2), float(xs[-1] + width / pixels_x / 2)],
            "im_range": [float(ys[-1] - height / pixels_y / 2), float(ys[0] + height / pixels_y / 2)],
        },
        "units": "dimensionless (complex plane)",
        "assumptions": [f"Escape radius 256, at most {max_iter} iterations; points that never escape are counted as inside",
                        "Area is a pixel-count estimate; it converges slowly (the true Mandelbrot area is about 1.5066)",
                        "A Julia set is connected exactly when c lies in the Mandelbrot set"],
    }
