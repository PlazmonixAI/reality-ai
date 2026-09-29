"""Geometric optics: thin lenses and spherical mirrors (with principal rays), Snell's law and Fresnel reflectance."""
import math

from app.core.registry import tool

_KINDS = ("converging_lens", "diverging_lens", "concave_mirror", "convex_mirror")


@tool(
    domain="physics",
    name="lens_mirror",
    description=(
        "Thin lens / spherical mirror imaging with 1/f = 1/d_o + 1/d_i. kind: converging_lens, diverging_lens, "
        "concave_mirror or convex_mirror; focal_length is its magnitude (m). Returns image distance, "
        "magnification, real/virtual, upright/inverted and the three principal rays as polylines for drawing "
        "(optic at x = 0, object on the left at x = -object_distance). Example: kind='converging_lens', "
        "focal_length=0.1, object_distance=0.3, object_height=0.02."
    ),
)
def lens_mirror(kind: str, focal_length: float, object_distance: float, object_height: float = 0.01) -> dict:
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}")
    if focal_length <= 0 or object_distance <= 0:
        raise ValueError("focal_length (magnitude) and object_distance must be positive")
    f = focal_length if kind in ("converging_lens", "concave_mirror") else -focal_length
    mirror = kind.endswith("mirror")
    do, ho = object_distance, object_height

    at_focus = math.isclose(do, f, rel_tol=1e-9)
    di = math.inf if at_focus else 1 / (1 / f - 1 / do)
    m = -di / do if not at_focus else math.inf
    hi = m * ho if not at_focus else math.inf

    # Coordinates: optic at x = 0, object at x = -do. Real images are on the outgoing side:
    # +x for a lens, -x for a mirror (light comes back).
    out = -1 if mirror else 1
    image_x = None if at_focus else out * di
    reach = 3 * max(do, abs(di) if not at_focus else do, abs(f))
    tip = (-do, ho)

    def ray(slope_after: float, y_at_optic: float) -> list[list[float]]:
        """Incoming segment from the object tip to the optic, then outgoing along slope (per unit out)."""
        end = (out * reach, y_at_optic + slope_after * reach)
        return [[tip[0], tip[1]], [0.0, y_at_optic], [end[0], end[1]]]

    # 1) parallel to axis, then through (or away from) the focal point
    r1 = ray(-ho / f, ho)
    # 2) through the centre of the lens (undeviated) / to the mirror vertex (reflects symmetrically)
    r2 = ray(-ho / do, 0.0)
    # 3) toward the (near-side) focal point, leaving parallel to the axis
    y3 = ho * f / (f - do) if not at_focus else None
    rays = [r1, r2]
    if y3 is not None:
        rays.append(ray(0.0, y3))
    # Virtual images: extend outgoing rays backwards (dashed in the UI).
    extensions = []
    if not at_focus and di < 0:
        for r in rays:
            extensions.append([r[1], [image_x, hi]])

    return {
        "result": {
            "image_distance": None if at_focus else di,
            "magnification": None if at_focus else m,
            "image_height": None if at_focus else hi,
            "image_type": "none (object at the focal point: rays leave parallel)" if at_focus
            else ("real" if di > 0 else "virtual"),
            "orientation": None if at_focus else ("upright" if m > 0 else "inverted"),
            "signed_focal_length": f,
        },
        "geometry": {
            "object": {"x": -do, "height": ho},
            "image": None if at_focus else {"x": image_x, "height": hi},
            "focal_points": [-f, f] if not mirror else [-f],
            "rays": rays,
            "virtual_extensions": extensions,
            "mirror": mirror,
        },
        "units": "distances and heights in m (image_distance > 0 means a real image); magnification dimensionless",
        "assumptions": [
            "Paraxial thin-lens / spherical-mirror equation 1/f = 1/do + 1/di",
            "Real-is-positive sign convention; diverging lens and convex mirror have f < 0",
        ],
    }


@tool(
    domain="physics",
    name="refraction",
    description=(
        "Light crossing a boundary between refractive indices n1 -> n2 at an angle of incidence (degrees from "
        "the normal): Snell's law refraction angle, critical angle, total internal reflection, Brewster angle and "
        "Fresnel reflectance/transmittance for s, p and unpolarised light. Example: n1=1.0, n2=1.33, "
        "incidence_deg=45."
    ),
)
def refraction(n1: float, n2: float, incidence_deg: float) -> dict:
    if n1 < 1 or n2 < 1:
        raise ValueError("Refractive indices must be >= 1")
    if not 0 <= incidence_deg < 90:
        raise ValueError("incidence_deg must be in [0, 90)")
    t1 = math.radians(incidence_deg)
    s2 = n1 / n2 * math.sin(t1)
    critical = math.degrees(math.asin(n2 / n1)) if n1 > n2 else None
    brewster = math.degrees(math.atan(n2 / n1))
    if s2 > 1:
        return {
            "result": {"refraction_deg": None, "total_internal_reflection": True, "reflectance": 1.0,
                       "reflectance_s": 1.0, "reflectance_p": 1.0, "transmittance": 0.0,
                       "critical_angle_deg": critical, "brewster_angle_deg": brewster},
            "units": "angles in degrees from the normal; reflectance/transmittance are power fractions",
            "assumptions": ["Snell's law; beyond the critical angle all light is reflected"],
        }
    t2 = math.asin(s2)
    c1, c2 = math.cos(t1), math.cos(t2)
    rs = ((n1 * c1 - n2 * c2) / (n1 * c1 + n2 * c2)) ** 2
    rp = ((n1 * c2 - n2 * c1) / (n1 * c2 + n2 * c1)) ** 2
    r = (rs + rp) / 2
    return {
        "result": {
            "refraction_deg": math.degrees(t2),
            "total_internal_reflection": False,
            "reflectance": r, "reflectance_s": rs, "reflectance_p": rp, "transmittance": 1 - r,
            "critical_angle_deg": critical, "brewster_angle_deg": brewster,
            "speed_ratio": n1 / n2,
        },
        "units": "angles in degrees from the normal; reflectance/transmittance are power fractions",
        "assumptions": ["Snell's law n1 sin(t1) = n2 sin(t2)", "Fresnel equations for non-absorbing, non-magnetic media"],
    }
