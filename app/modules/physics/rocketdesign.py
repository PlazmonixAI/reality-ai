"""Design your own hardware: liquid rocket engines (ideal-rocket thermodynamics with real-engine efficiencies),
satellites (mass, power and eclipse budget) and the Earth→Moon transfer (patched conics).

Outputs include a `part` spec that can be passed to rocket_design / rocket_flight as a custom part."""
import math

import numpy as np
from scipy.optimize import brentq

from app.core.registry import tool
from app.modules.physics.rocketry import BODIES, G0, MOON_DISTANCE, MOON_RADIUS, MU_MOON, engine_class

P_SL = 101_325.0
R_UNIVERSAL = 8314.462618

# Effective chamber-gas properties at typical mixture ratios, calibrated so the ideal-rocket model reproduces real
# engines (Merlin 1D, F-1, RD-180, RS-25, RL10, Vulcain 2, Raptor, Aestus, AJ10) within a few percent:
# O/F mass ratio, chamber temperature K, molar mass kg/kmol, ratio of specific heats, characteristic length L* m
PROPELLANTS = {
    "lox_rp1": {"name": "LOX / RP-1 kerosene", "of": 2.6, "tc": 3303.0, "mw": 21.5, "gamma": 1.158, "lstar": 1.1},
    "lox_lh2": {"name": "LOX / liquid hydrogen", "of": 6.0, "tc": 3080.0, "mw": 12.38, "gamma": 1.15, "lstar": 0.8},
    "lox_ch4": {"name": "LOX / liquid methane", "of": 3.6, "tc": 3195.0, "mw": 18.29, "gamma": 1.158, "lstar": 1.0},
    "nto_mmh": {"name": "N₂O₄ / MMH (hypergolic)", "of": 2.0, "tc": 2808.0, "mw": 20.12, "gamma": 1.178, "lstar": 0.9},
}
# Engine cycles: max practical chamber pressure (bar), typical vacuum thrust-to-weight, Isp factor for the
# turbine exhaust (gas-generator cycles dump a few % of the flow at low Isp)
CYCLES = {
    "pressure_fed": {"name": "Pressure-fed", "pc_max": 30, "tw": 27, "isp_factor": 1.0},
    "electric_pump": {"name": "Electric pump", "pc_max": 50, "tw": 75, "isp_factor": 1.0},
    "gas_generator": {"name": "Gas generator", "pc_max": 120, "tw": 150, "isp_factor": 0.975},
    "expander": {"name": "Expander", "pc_max": 70, "tw": 38, "isp_factor": 1.0},
    "staged_combustion": {"name": "Staged combustion", "pc_max": 300, "tw": 78, "isp_factor": 1.0},
    "full_flow": {"name": "Full-flow staged combustion", "pc_max": 350, "tw": 145, "isp_factor": 1.0},
}
ETA_CSTAR = 0.975  # combustion efficiency


def area_ratio(mach: float, gamma: float) -> float:
    """Isentropic A/A* for a given Mach number."""
    g = gamma
    return (1 / mach) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * mach * mach)) ** ((g + 1) / (2 * (g - 1)))


def exit_mach(eps: float, gamma: float) -> float:
    """Supersonic Mach number for area ratio eps."""
    if eps <= 1:
        return 1.0
    return brentq(lambda m: area_ratio(m, gamma) - eps, 1.0 + 1e-9, 60.0)


def pressure_ratio(mach: float, gamma: float) -> float:
    """p/p0 for isentropic flow."""
    return (1 + (gamma - 1) / 2 * mach * mach) ** (-gamma / (gamma - 1))


def cstar(tc: float, mw: float, gamma: float) -> float:
    g, r = gamma, R_UNIVERSAL / mw
    return math.sqrt(g * r * tc) / (g * math.sqrt((2 / (g + 1)) ** ((g + 1) / (g - 1))))


def thrust_coefficient(eps: float, gamma: float, pc: float, pa: float, lam: float = 1.0) -> tuple[float, float]:
    """Thrust coefficient (momentum term × divergence factor lam + pressure term) and exit pressure pe."""
    g = gamma
    pe = pc * pressure_ratio(exit_mach(eps, g), g)
    mom = math.sqrt(2 * g * g / (g - 1) * (2 / (g + 1)) ** ((g + 1) / (g - 1)) * (1 - (pe / pc) ** ((g - 1) / g)))
    return lam * mom + eps * (pe - pa) / pc, pe


@tool(
    domain="physics",
    name="rocket_engine_design",
    description=(
        "Design a liquid rocket engine from first principles: propellant (lox_rp1, lox_lh2, lox_ch4, nto_mmh), cycle "
        "(pressure_fed, electric_pump, gas_generator, expander, staged_combustion, full_flow), chamber pressure (bar), "
        "nozzle expansion ratio and target vacuum thrust (kN). Returns c*, exit Mach and pressure, thrust coefficient, "
        "Isp and thrust at sea level and in vacuum (with flow-separation check), mass flow, throat/exit/chamber sizes, "
        "engine length, estimated mass and thrust-to-weight, a nozzle profile for drawing, thrust vs altitude, and a "
        "ready-to-use custom part. Example: propellant='lox_rp1', cycle='gas_generator', chamber_pressure_bar=97, "
        "expansion_ratio=16, thrust_vac_kn=914 (≈ Merlin 1D)."
    ),
)
def rocket_engine_design(propellant: str = "lox_rp1", cycle: str = "gas_generator", chamber_pressure_bar: float = 97.0,
                         expansion_ratio: float = 16.0, thrust_vac_kn: float = 900.0, nozzle: str = "bell",
                         name: str = "My engine") -> dict:
    if propellant not in PROPELLANTS:
        raise ValueError(f"propellant must be one of {', '.join(PROPELLANTS)}")
    if cycle not in CYCLES:
        raise ValueError(f"cycle must be one of {', '.join(CYCLES)}")
    if nozzle not in ("bell", "cone"):
        raise ValueError("nozzle must be 'bell' or 'cone'")
    if not 2 <= chamber_pressure_bar <= 400:
        raise ValueError("chamber_pressure_bar must be between 2 and 400")
    if not 2 <= expansion_ratio <= 400:
        raise ValueError("expansion_ratio must be between 2 and 400")
    if not 0.1 <= thrust_vac_kn <= 12_000:
        raise ValueError("thrust_vac_kn must be between 0.1 and 12,000 kN")
    pr, cy = PROPELLANTS[propellant], CYCLES[cycle]
    g, pc, eps = pr["gamma"], chamber_pressure_bar * 1e5, expansion_ratio
    lam = 0.985 if nozzle == "bell" else (1 + math.cos(math.radians(15))) / 2
    c_star = cstar(pr["tc"], pr["mw"], g) * ETA_CSTAR
    me = exit_mach(eps, g)
    cf_vac, pe = thrust_coefficient(eps, g, pc, 0.0, lam)
    # Sea level: the flow separates from the wall where it would drop below ~0.25 × ambient (Schmucker-type criterion);
    # the nozzle then behaves as if cut off there.
    separated = pe < 0.25 * P_SL
    if separated:
        m_sep = brentq(lambda m: pc * pressure_ratio(m, g) - 0.25 * P_SL, 1.0 + 1e-9, me)
        cf_sl, _ = thrust_coefficient(area_ratio(m_sep, g), g, pc, P_SL, lam)
    else:
        cf_sl, _ = thrust_coefficient(eps, g, pc, P_SL, lam)
    isp_vac = c_star * cf_vac * cy["isp_factor"] / G0
    isp_sl = max(c_star * cf_sl * cy["isp_factor"] / G0, 1.0)
    f_vac = thrust_vac_kn * 1e3
    at = f_vac / (cf_vac * pc)
    mdot = f_vac / (isp_vac * G0)
    f_sl = mdot * isp_sl * G0
    dt_, de = math.sqrt(4 * at / math.pi), math.sqrt(4 * at * eps / math.pi)
    dc = dt_ * math.sqrt(3.0)  # contraction ratio 3
    l_chamber = pr["lstar"] * at / (math.pi * dc * dc / 4)
    l_conv = (dc - dt_) / 2  # 45° convergent cone
    l_nozzle = (de - dt_) / 2 / math.tan(math.radians(15)) * (0.8 if nozzle == "bell" else 1.0)
    l_head = 0.5 * dc + 0.15  # injector and turbomachinery
    length = l_head + l_chamber + l_conv + l_nozzle
    mass = f_vac / (cy["tw"] * G0)
    warnings = []
    if chamber_pressure_bar > cy["pc_max"]:
        warnings.append(f"{cy['name']} engines rarely exceed {cy['pc_max']} bar chamber pressure")
    if separated:
        warnings.append("at sea level the nozzle is over-expanded and the flow separates: use this engine in vacuum stages")
    elif pe > 3 * P_SL:
        warnings.append("strongly under-expanded at sea level: a larger expansion ratio would add thrust")
    # Nozzle profile for drawing (z down from the injector, radius), metres
    prof = [[0.0, dc / 2], [l_head + l_chamber, dc / 2], [l_head + l_chamber + l_conv, dt_ / 2]]
    z0, r0, z1, r1 = l_head + l_chamber + l_conv, dt_ / 2, length, de / 2
    th_n, th_e = (math.radians(30), math.radians(8)) if nozzle == "bell" else (math.radians(15), math.radians(15))
    zc = (r1 - r0 - math.tan(th_e) * z1 + math.tan(th_n) * z0) / (math.tan(th_n) - math.tan(th_e)) if nozzle == "bell" else z0
    rc = r0 + math.tan(th_n) * (zc - z0)
    for u in np.linspace(0, 1, 16)[1:]:  # quadratic Bézier from the throat to the exit (Rao-style bell)
        z = (1 - u) ** 2 * z0 + 2 * u * (1 - u) * zc + u * u * z1
        r = (1 - u) ** 2 * r0 + 2 * u * (1 - u) * rc + u * u * r1
        prof.append([z, r])
    alts = np.array([0, 5, 10, 20, 30, 50, 80]) * 1e3
    thrust_alt = []
    for h in alts:
        pa = P_SL * math.exp(-h / 8500.0)
        cf, _ = thrust_coefficient(eps, g, pc, pa, lam)
        if pe < 0.25 * pa:
            m_sep = brentq(lambda m: pc * pressure_ratio(m, g) - 0.25 * pa, 1.0 + 1e-9, me)
            cf, _ = thrust_coefficient(area_ratio(m_sep, g), g, pc, pa, lam)
        thrust_alt.append({"altitude_km": h / 1000, "thrust_kn": max(cf, 0.0) * pc * at / 1e3,
                           "isp": max(c_star * cf * cy["isp_factor"] / G0, 0.0)})
    width = max(de, dc) * 1.12
    part = {"category": "engine", "name": str(name)[:40] or "My engine", "mass": round(mass, 1), "height": round(length, 3),
            "width": round(width, 3), "thrust_sl": round(max(f_sl, f_vac * 0.01), 1), "thrust_vac": round(f_vac, 1),
            "isp_sl": round(max(isp_sl, 1.0), 2), "isp_vac": round(isp_vac, 2)}
    return {
        "result": {
            "propellant": pr["name"], "cycle": cy["name"], "mixture_ratio": pr["of"], "chamber_temperature": pr["tc"],
            "characteristic_velocity": c_star, "exit_mach": me, "exit_pressure": pe,
            "thrust_coefficient_vac": cf_vac, "thrust_coefficient_sl": cf_sl,
            "isp_vac": isp_vac, "isp_sl": isp_sl, "thrust_vac": f_vac, "thrust_sl": f_sl, "mass_flow": mdot,
            "fuel_flow": mdot / (1 + pr["of"]), "oxidizer_flow": mdot * pr["of"] / (1 + pr["of"]),
            "throat_diameter": dt_, "exit_diameter": de, "chamber_diameter": dc, "length": length,
            "mass": mass, "thrust_to_weight": f_vac / (mass * G0), "size_class": engine_class(f_vac),
            "sea_level_flow_separation": separated, "profile": prof, "thrust_vs_altitude": thrust_alt,
            "warnings": warnings, "part": part,
        },
        "units": "SI: N, kg/s, m, Pa, K, m/s; Isp in s",
        "assumptions": [
            "Ideal-rocket (isentropic, one-dimensional) nozzle flow with effective chamber-gas properties for the propellant",
            f"Combustion efficiency {ETA_CSTAR}, divergence factor {lam:.3f} ({nozzle} nozzle); gas-generator cycles lose "
            "2.5 % Isp to turbine exhaust",
            "Sea-level flow separation where wall pressure < 0.25 × ambient; the nozzle then acts as if cut off there",
            "Mass from a typical thrust-to-weight for the cycle; chamber sized with contraction ratio 3 and the propellant's L*",
        ],
    }


# ---------- satellites ----------
THRUSTERS = {  # Isp s, thrust N, dry mass kg (+10 % of propellant for tanks)
    "none": (0.0, 0.0, 0.0), "cold_gas": (70.0, 1.0, 1.0), "hydrazine": (220.0, 22.0, 5.0),
    "bipropellant": (318.0, 450.0, 20.0), "ion": (3000.0, 0.09, 35.0),
}
AVIONICS = {"cubesat": 1.5, "small": 40.0, "medium": 150.0, "large": 350.0}
SOLAR_CONSTANT = 1361.0


@tool(
    domain="physics",
    name="satellite_design",
    description=(
        "Design a satellite: bus size (cubesat, small, medium, large), payload/instrument mass, solar array area and "
        "cell efficiency, battery capacity, electrical load, propellant and thruster (none, cold_gas, hydrazine, "
        "bipropellant, ion) and a circular orbit altitude. Returns the mass budget (dry and wet), Δv, orbital period, "
        "worst-case eclipse time, power generated and the energy balance, battery depth of discharge, and a custom "
        "part to put on a rocket. Example: bus='medium', payload_kg=300, solar_area_m2=12, battery_wh=3000, "
        "power_draw_w=1500, propellant_kg=200, thruster='hydrazine', altitude_km=700."
    ),
)
def satellite_design(bus: str = "medium", payload_kg: float = 300.0, solar_area_m2: float = 10.0, cell_efficiency: float = 0.3,
                     battery_wh: float = 3000.0, power_draw_w: float = 1200.0, propellant_kg: float = 150.0,
                     thruster: str = "hydrazine", altitude_km: float = 700.0, name: str = "My satellite") -> dict:
    if bus not in AVIONICS:
        raise ValueError(f"bus must be one of {', '.join(AVIONICS)}")
    if thruster not in THRUSTERS:
        raise ValueError(f"thruster must be one of {', '.join(THRUSTERS)}")
    if not (0 <= payload_kg <= 20000 and 0 <= solar_area_m2 <= 500 and 0.05 <= cell_efficiency <= 0.5
            and 0 <= battery_wh <= 500000 and 0 <= power_draw_w <= 50000 and 0 <= propellant_kg <= 50000):
        raise ValueError("payload 0..20 t, solar area 0..500 m², efficiency 0.05..0.5, battery 0..500 kWh, load 0..50 kW, propellant 0..50 t")
    if not 160 <= altitude_km <= 400_000:
        raise ValueError("altitude_km must be between 160 and 400,000")
    if thruster == "none" and propellant_kg > 0:
        raise ValueError("propellant needs a thruster")
    isp, thrust, thr_mass = THRUSTERS[thruster]
    array_mass, battery_mass = 3.0 * solar_area_m2, battery_wh / 150.0
    prop_dry = (thr_mass + 0.1 * propellant_kg) if thruster != "none" else 0.0
    subsystems = payload_kg + array_mass + battery_mass + AVIONICS[bus] + prop_dry
    structure = subsystems * 0.2 / 0.8  # structure and thermal ≈ 20 % of the dry mass
    dry = subsystems + structure
    wet = dry + propellant_kg
    dv = isp * G0 * math.log(wet / dry) if propellant_kg > 0 else 0.0
    mu, re = BODIES["earth"]["mu"], BODIES["earth"]["radius"]
    a = re + altitude_km * 1e3
    period = 2 * math.pi * math.sqrt(a**3 / mu)
    ecl_frac = math.asin(re / a) / math.pi  # orbit in the Sun's plane (β = 0): the longest eclipse
    p_sun = SOLAR_CONSTANT * cell_efficiency * solar_area_m2 * 0.85  # packing and wiring losses
    p_avg = p_sun * (1 - ecl_frac)
    e_eclipse = power_draw_w * period * ecl_frac / 3600 / 0.9  # Wh drawn from the battery (90 % discharge efficiency)
    dod = e_eclipse / battery_wh if battery_wh > 0 else float("inf")
    dod_limit = 0.3 if altitude_km < 10_000 else 0.7  # LEO: ~15 cycles a day, so shallow cycling
    ok_power = p_avg >= power_draw_w / 0.9
    warnings = []
    if not ok_power:
        warnings.append(f"the array averages {p_avg:.0f} W over an orbit but the load needs {power_draw_w / 0.9:.0f} W: add area or efficiency")
    if dod > dod_limit:
        warnings.append(f"eclipses drain {dod * 100:.0f} % of the battery (keep below {dod_limit * 100:.0f} % for a long life)")
    side = max(0.1, (dry / 200.0) ** (1 / 3))  # ~200 kg/m³ bus density
    part = {"category": "satellite", "name": str(name)[:40] or "My satellite", "mass": round(dry, 2), "height": round(side * 1.3, 3),
            "width": round(side, 3)}
    if propellant_kg > 0:
        part.update({"prop": round(propellant_kg, 2), "thrust_vac": thrust, "thrust_sl": thrust * 0.5, "isp_vac": isp,
                     "isp_sl": isp * 0.5})
    return {
        "result": {
            "dry_mass": dry, "wet_mass": wet, "structure_mass": structure, "solar_array_mass": array_mass,
            "battery_mass": battery_mass, "propulsion_dry_mass": prop_dry, "delta_v": dv, "thrust": thrust,
            "orbital_period": period, "eclipse_fraction": ecl_frac, "eclipse_duration": period * ecl_frac,
            "power_in_sunlight": p_sun, "orbit_average_power": p_avg, "battery_depth_of_discharge": dod,
            "power_ok": ok_power and dod <= dod_limit, "warnings": warnings, "part": part,
        },
        "units": "kg, m/s, s, W, Wh; depth of discharge as a fraction",
        "assumptions": [
            "Sun-tracking arrays at 1 AU (1361 W/m²) with 15 % packing/wiring loss; eclipse for an orbit in the Sun's plane",
            "Arrays 3 kg/m², Li-ion batteries 150 Wh/kg, structure 20 % of dry mass, tanks 10 % of propellant",
            "Δv from the rocket equation with the thruster's Isp",
        ],
    }


# ---------- Earth → Moon ----------
@tool(
    domain="physics",
    name="lunar_transfer",
    description=(
        "Plan a trip from a circular Earth parking orbit to the Moon with patched conics: trans-lunar injection Δv, "
        "transfer time, the Moon's required lead angle at departure, arrival excess speed, lunar-orbit insertion Δv, "
        "lunar orbit period, landing and ascent Δv, trans-Earth injection and the total budget. Example: "
        "parking_altitude_km=200, lunar_orbit_altitude_km=100."
    ),
)
def lunar_transfer(parking_altitude_km: float = 200.0, lunar_orbit_altitude_km: float = 100.0) -> dict:
    if not 150 <= parking_altitude_km <= 50_000 or not 10 <= lunar_orbit_altitude_km <= 20_000:
        raise ValueError("parking_altitude_km must be 150..50,000 and lunar_orbit_altitude_km 10..20,000")
    mu, re = BODIES["earth"]["mu"], BODIES["earth"]["radius"]
    r0, d = re + parking_altitude_km * 1e3, MOON_DISTANCE
    vc = math.sqrt(mu / r0)
    at = (r0 + d) / 2
    v_dep = math.sqrt(mu * (2 / r0 - 1 / at))
    t_tr = math.pi * math.sqrt(at**3 / mu)
    n_moon = math.sqrt((mu + MU_MOON) / d**3)
    lead = math.pi - n_moon * t_tr
    v_arr = math.sqrt(mu * (2 / d - 1 / at))
    v_inf = n_moon * d - v_arr
    rl = MOON_RADIUS + lunar_orbit_altitude_km * 1e3
    v_llo = math.sqrt(MU_MOON / rl)
    v_peri = math.sqrt(v_inf**2 + 2 * MU_MOON / rl)
    loi = v_peri - v_llo
    a_desc = (rl + MOON_RADIUS) / 2  # Hohmann descent to the surface, then cancel the remaining speed
    descent = v_llo - math.sqrt(MU_MOON * (2 / rl - 1 / a_desc)) + math.sqrt(MU_MOON * (2 / MOON_RADIUS - 1 / a_desc))
    moon_rot = 2 * math.pi * MOON_RADIUS / (27.321661 * 86400)
    return {
        "result": {
            "parking_orbit_speed": vc, "tli_delta_v": v_dep - vc, "transfer_time": t_tr, "transfer_time_days": t_tr / 86400,
            "moon_lead_angle_deg": math.degrees(lead), "arrival_speed_vs_moon": v_inf, "loi_delta_v": loi,
            "lunar_orbit_speed": v_llo, "lunar_orbit_period": 2 * math.pi * math.sqrt(rl**3 / MU_MOON),
            "landing_delta_v_ideal": descent - moon_rot, "ascent_delta_v_ideal": descent - moon_rot,
            "tei_delta_v": loi, "total_one_way_to_surface": (v_dep - vc) + loi + descent - moon_rot,
            "total_round_trip_from_leo": (v_dep - vc) + 2 * loi + 2 * (descent - moon_rot),
        },
        "units": "m/s, s, degrees",
        "assumptions": [
            "Patched conics: a Hohmann-like transfer ellipse to the Moon's mean distance, then a hyperbola inside its sphere of influence",
            "Coplanar circular orbits; ideal impulsive burns (no gravity losses or plane changes)",
            "Returning uses aerobraking at Earth, so the round trip needs TLI + LOI + landing + ascent + TEI",
        ],
    }
