"""Complex numbers on the plane and 2D linear transformations."""
import cmath
import math

import numpy as np

from app.core.registry import tool


@tool(
    domain="mathematics",
    name="complex_numbers",
    description=(
        "Complex arithmetic for z = a + bi and w = c + di: polar forms (modulus, argument), sum, product, "
        "quotient, conjugate, and the n-th roots of z. Example: z=[1,1], w=[0,2], n=3."
    ),
)
def complex_numbers(z: list[float], w: list[float] | None = None, n: int = 3) -> dict:
    if len(z) != 2 or (w is not None and len(w) != 2):
        raise ValueError("z and w must be [real, imaginary]")
    if not 1 <= n <= 24:
        raise ValueError("n must be 1..24")
    zc = complex(z[0], z[1])
    wc = complex(w[0], w[1]) if w is not None else None
    pair = lambda c: [c.real, c.imag]   # noqa: E731
    polar = lambda c: {"modulus": abs(c), "argument_deg": math.degrees(cmath.phase(c))}   # noqa: E731
    r, th = abs(zc), cmath.phase(zc)
    roots = [pair(cmath.rect(r ** (1 / n), (th + 2 * math.pi * k) / n)) for k in range(n)] if r else [[0.0, 0.0]]
    out = {"z": pair(zc), "z_polar": polar(zc), "conjugate": pair(zc.conjugate()), "roots": roots}
    if wc is not None:
        out.update({"w": pair(wc), "w_polar": polar(wc), "sum": pair(zc + wc), "product": pair(zc * wc),
                    "product_polar": polar(zc * wc), "quotient": pair(zc / wc) if wc else None})
    return {
        "result": out,
        "units": "dimensionless; arguments in degrees in (-180, 180]",
        "assumptions": ["Principal argument; n-th roots are equally spaced on a circle of radius |z|^(1/n)"],
    }


@tool(
    domain="mathematics",
    name="linear_transform_2d",
    description=(
        "Apply a 2x2 matrix to the plane: determinant (area scale / orientation), trace, eigenvalues and real "
        "eigenvectors, images of the basis vectors, the unit square and grid lines for drawing, and the "
        "transformation type. Example: matrix=[[2,1],[1,2]]."
    ),
)
def linear_transform_2d(matrix: list[list[float]], grid: int = 5) -> dict:
    A = np.array(matrix, dtype=float)
    if A.shape != (2, 2) or not np.all(np.isfinite(A)):
        raise ValueError("matrix must be 2x2 with finite entries")
    if not 1 <= grid <= 10:
        raise ValueError("grid must be 1..10")
    det, tr = float(np.linalg.det(A)), float(np.trace(A))
    vals, vecs = np.linalg.eig(A)
    real = np.all(np.abs(vals.imag) < 1e-12)
    eig = [{"value": float(vals[k].real), "vector": (vecs[:, k].real / np.linalg.norm(vecs[:, k].real)).tolist()}
           for k in range(2)] if real else [{"value": [float(v.real), float(v.imag)], "vector": None} for v in vals]
    if np.allclose(A, A[0, 0] * np.eye(2)):
        kind = "uniform scaling" if not math.isclose(A[0, 0], 1) else "identity"
    elif math.isclose(abs(det), 1, abs_tol=1e-9) and np.allclose(A.T @ A, np.eye(2)):
        kind = "rotation" if det > 0 else "reflection"
    elif math.isclose(det, 0, abs_tol=1e-12):
        kind = "projection onto a line (singular)"
    elif real and not np.allclose(A, A.T) and np.allclose(vals, vals[0]):
        kind = "shear"
    else:
        kind = "general linear map" + (" (orientation reversing)" if det < 0 else "")
    lines = []
    for k in range(-grid, grid + 1):
        for p, q in (([k, -grid], [k, grid]), ([-grid, k], [grid, k])):
            lines.append([(A @ p).tolist(), (A @ q).tolist()])
    square = [(A @ v).tolist() for v in ([0, 0], [1, 0], [1, 1], [0, 1])]
    return {
        "result": {"determinant": det, "trace": tr, "eigen": eig, "real_eigenvalues": bool(real), "type": kind,
                   "e1_image": A[:, 0].tolist(), "e2_image": A[:, 1].tolist()},
        "unit_square": square,
        "grid_lines": lines,
        "units": "dimensionless",
        "assumptions": ["Eigenvectors normalised; complex eigenvalues are given as [re, im] with no real eigenvector"],
    }
