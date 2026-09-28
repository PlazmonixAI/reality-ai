"""VSEPR molecular shapes: domain counting from a formula and electron-domain positions by repulsion minimisation."""
import itertools
import math

import numpy as np
from scipy.optimize import minimize

from app.core.registry import tool
from app.modules.chemistry.formula import element_counts, split_species

# Valence electrons of main-group elements that commonly appear in VSEPR problems.
VALENCE = {
    "H": 1, "Be": 2, "B": 3, "Al": 3, "C": 4, "Si": 4, "Ge": 4, "Sn": 4, "N": 5, "P": 5, "As": 5, "Sb": 5,
    "O": 6, "S": 6, "Se": 6, "Te": 6, "F": 7, "Cl": 7, "Br": 7, "I": 7, "Xe": 8, "Kr": 8,
}
# Electrons of the central atom used to bond each terminal atom (single bond to H/halogens, double to O/S/Se).
BOND_ELECTRONS = {"H": 1, "F": 1, "Cl": 1, "Br": 1, "I": 1, "O": 2, "S": 2, "Se": 2, "N": 3}

ELECTRON_GEOMETRY = {2: "linear", 3: "trigonal planar", 4: "tetrahedral", 5: "trigonal bipyramidal", 6: "octahedral"}
MOLECULAR_GEOMETRY = {
    (2, 0): "linear", (3, 0): "trigonal planar", (2, 1): "bent", (4, 0): "tetrahedral", (3, 1): "trigonal pyramidal",
    (2, 2): "bent", (5, 0): "trigonal bipyramidal", (4, 1): "seesaw", (3, 2): "T-shaped", (2, 3): "linear",
    (6, 0): "octahedral", (5, 1): "square pyramidal", (4, 2): "square planar", (1, 0): "linear", (1, 1): "linear",
    (1, 2): "linear", (1, 3): "linear",
}
LP_WEIGHT = {("L", "L"): 1.6, ("B", "L"): 1.25, ("L", "B"): 1.25, ("B", "B"): 1.0}


def arrange_domains(kinds: list[str], weighted: bool, seed: int = 0) -> np.ndarray:
    """Unit vectors for electron domains minimising sum w_ij / |r_i - r_j| on the unit sphere (Thomson-like)."""
    n = len(kinds)
    if n == 1:
        return np.array([[0.0, 0.0, 1.0]])
    w = np.array([[LP_WEIGHT[(a, b)] if weighted else 1.0 for b in kinds] for a in kinds])
    iu = np.triu_indices(n, 1)

    def energy(flat):
        p = flat.reshape(n, 3)
        p = p / np.linalg.norm(p, axis=1, keepdims=True)
        d = np.linalg.norm(p[:, None] - p[None], axis=-1)[iu]
        return float(np.sum(w[iu] / d))

    rng = np.random.default_rng(seed)
    best = None
    for _ in range(12):
        res = minimize(energy, rng.normal(size=3 * n), method="BFGS", options={"gtol": 1e-10, "maxiter": 5000})
        if best is None or res.fun < best.fun - 1e-12:
            best = res
    p = best.x.reshape(n, 3)
    p /= np.linalg.norm(p, axis=1, keepdims=True)
    # Orient canonically: first bonding domain along +z, second in the xz-plane.
    b = [i for i, k in enumerate(kinds) if k == "B"] or [0]
    z = p[b[0]]
    ref = p[b[1]] if len(b) > 1 else (p[1] if n > 1 else np.array([1.0, 0, 0]))
    x = ref - (ref @ z) * z
    x = x / np.linalg.norm(x) if np.linalg.norm(x) > 1e-9 else np.cross(z, [0, 1, 0]) / np.linalg.norm(np.cross(z, [0, 1, 0]))
    y = np.cross(z, x)
    return p @ np.column_stack([x, y, z])


def bond_angles(p: np.ndarray, kinds: list[str]) -> list[float]:
    b = [i for i, k in enumerate(kinds) if k == "B"]
    angs = sorted({round(math.degrees(math.acos(np.clip(p[i] @ p[j], -1, 1))), 2) for i, j in itertools.combinations(b, 2)})
    # merge values within 0.5 degree
    merged = []
    for a in angs:
        if not merged or a - merged[-1] > 0.5:
            merged.append(a)
    return merged


@tool(
    domain="chemistry",
    name="molecule_shape",
    description=(
        "VSEPR shape of a molecule or ion with one central atom, e.g. 'H2O', 'SF4', 'XeF4', 'NH4^+', 'CO3^2-'. "
        "Counts bonding domains and lone pairs from valence electrons (single bonds to H/halogens, double to "
        "terminal O/S), then finds the electron-domain arrangement by minimising repulsion. Returns AXE "
        "notation, electron and molecular geometry, bond angles and 3D domain directions (ideal and with "
        "stronger lone-pair repulsion). Alternatively give bonding_domains and lone_pairs directly."
    ),
)
def molecule_shape(formula: str | None = None, bonding_domains: int | None = None, lone_pairs: int | None = None) -> dict:
    central = None
    terminals: dict[str, int] = {}
    if formula is not None:
        sp = split_species(formula)
        counts = element_counts(sp.formula)
        candidates = [el for el, n in counts.items() if n == 1 and el != "H"]
        if not candidates:
            raise ValueError("Could not identify a single central atom (e.g. 'CH4', 'SF6', 'NO3^-')")
        # Central atom: the least electronegative-ish single atom; prefer the one written first.
        order = [el for el in _element_order(sp.formula) if el in candidates]
        central = next((el for el in order if el not in ("F", "O") or len(order) == 1), order[0])
        terminals = {el: n for el, n in counts.items() if el != central}
        terminals.update({central: counts[central] - 1} if counts[central] > 1 else {})
        terminals = {k: v for k, v in terminals.items() if v}
        if central not in VALENCE:
            raise ValueError(f"No valence data for central atom {central}")
        for el in terminals:
            if el not in BOND_ELECTRONS:
                raise ValueError(f"Terminal atom {el} not supported (use H, halogens, O, S, Se or N)")
        x = sum(terminals.values())
        e2 = VALENCE[central] - sp.charge - sum(BOND_ELECTRONS[el] * n for el, n in terminals.items())
        if e2 < 0 or e2 % 2:
            raise ValueError(f"Electron count for {formula} does not give whole lone pairs; check the formula/charge")
        bonding_domains, lone_pairs = x, e2 // 2
    if bonding_domains is None or lone_pairs is None:
        raise ValueError("Give a formula, or bonding_domains and lone_pairs")
    n = bonding_domains + lone_pairs
    if bonding_domains < 1 or lone_pairs < 0 or not 2 <= n <= 6 and not (bonding_domains == 1 and n <= 4):
        raise ValueError("Supported: 2 to 6 electron domains around the central atom")
    kinds = ["B"] * bonding_domains + ["L"] * lone_pairs
    real = arrange_domains(kinds, weighted=True)
    ideal = _ideal_like(real, len(kinds))
    return {
        "result": {
            "central_atom": central,
            "axe": f"AX{bonding_domains}" + (f"E{lone_pairs}" if lone_pairs else ""),
            "steric_number": n,
            "electron_geometry": ELECTRON_GEOMETRY.get(n, "linear"),
            "molecular_geometry": MOLECULAR_GEOMETRY[(bonding_domains, lone_pairs)],
            "ideal_bond_angles": bond_angles(ideal, kinds),
            "compressed_bond_angles": bond_angles(real, kinds),
        },
        "terminals": terminals,
        "domains": {"kinds": kinds, "ideal": ideal.round(6).tolist(), "with_lone_pair_repulsion": real.round(6).tolist()},
        "units": "angles in degrees; domain directions are unit vectors",
        "assumptions": [
            "VSEPR: electron domains around one central atom repel; lone pairs repel more strongly",
            "Domains placed by minimising sum of w/r on a sphere; weights LP-LP 1.6, LP-BP 1.25, BP-BP 1 (qualitative)",
            "Terminal O/S counted as double bonds, H and halogens as single bonds",
        ],
    }


def _ideal_like(real: np.ndarray, n: int) -> np.ndarray:
    """Perfect n-domain geometry (equal repulsion), rotated and labelled to match the lone-pair-weighted one,
    so lone pairs keep the positions they prefer (e.g. equatorial in a trigonal bipyramid)."""
    perfect = arrange_domains(["B"] * n, weighted=False)
    best, best_err = None, math.inf
    for perm in itertools.permutations(range(n)):
        q = perfect[list(perm)]
        u, _, vt = np.linalg.svd(q.T @ real)          # Kabsch: rotation taking q onto real
        d = np.sign(np.linalg.det(u @ vt))
        rot = u @ np.diag([1, 1, d]) @ vt
        err = np.sum((q @ rot - real) ** 2)
        if err < best_err:
            best, best_err = q @ rot, err
    return best


def _element_order(formula: str) -> list[str]:
    import re
    return re.findall(r"[A-Z][a-z]?", formula)
