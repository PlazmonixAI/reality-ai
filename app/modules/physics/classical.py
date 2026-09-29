"""Classical mechanics: projectile motion (with/without quadratic drag), harmonic oscillators."""
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import ellipk

from app.core.registry import tool

G0 = 9.80665
MAX_POINTS = 10_000


@tool(
    domain="physics",
    name="projectile_motion",
    description=(
        "Projectile launched at speed (m/s) and angle_deg above horizontal from height (m). Without drag uses "
        "closed-form kinematics; give mass (kg), drag_coefficient and area (m^2) to include quadratic air drag "
        "(air_density default 1.225 kg/m^3). Returns range, max height, flight time, impact speed and a "
        "plot-ready trajectory. Example: speed=50, angle_deg=45."
    ),
)
def projectile_motion(
    speed: float,
    angle_deg: float,
    height: float = 0.0,
    gravity: float = G0,
    mass: float | None = None,
    drag_coefficient: float | None = None,
    area: float | None = None,
    air_density: float = 1.225,
    n_points: int = 201,
) -> dict:
    if speed < 0 or height < 0 or gravity <= 0 or air_density < 0:
        raise ValueError("speed, height and air_density must be >= 0 and gravity > 0")
    if not -90 <= angle_deg <= 90:
        raise ValueError("angle_deg must be between -90 and 90")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    drag_args = (mass, drag_coefficient, area)
    with_drag = any(a is not None for a in drag_args)
    if with_drag and (None in drag_args or min(drag_args) <= 0):
        raise ValueError("For drag give positive mass, drag_coefficient and area (all three)")
    if speed == 0 and height == 0:
        raise ValueError("Projectile has no speed and starts on the ground")

    th = math.radians(angle_deg)
    vx0, vy0 = speed * math.cos(th), speed * math.sin(th)

    if not with_drag:
        t_flight = (vy0 + math.sqrt(vy0**2 + 2 * gravity * height)) / gravity
        t = np.linspace(0, t_flight, n_points)
        x, y = vx0 * t, height + vy0 * t - 0.5 * gravity * t**2
        y[-1] = 0.0
        vy_end = vy0 - gravity * t_flight
        max_h = height + (vy0**2 / (2 * gravity) if vy0 > 0 else 0.0)
        result = {
            "range": vx0 * t_flight,
            "max_height": max_h,
            "flight_time": t_flight,
            "impact_speed": math.hypot(vx0, vy_end),
            "impact_angle_deg": math.degrees(math.atan2(-vy_end, vx0)),
        }
        assumptions = ["Uniform gravity, no air resistance", "Flat ground at y = 0"]
    else:
        k = 0.5 * air_density * drag_coefficient * area / mass  # drag accel = k v |v|

        def rhs(_t, s):
            v = math.hypot(s[2], s[3])
            return [s[2], s[3], -k * v * s[2], -gravity - k * v * s[3]]

        def ground(_t, s):
            return s[1]
        ground.terminal, ground.direction = True, -1

        # Upper bound on flight time: the vacuum flight time is never exceeded by more than terminal fall time.
        v_term = math.sqrt(gravity / k)
        t_max = 2 * (speed + v_term) / gravity + 2 * height / v_term + 10
        sol = solve_ivp(rhs, (0, t_max), [0.0, height, vx0, vy0], events=ground, method="DOP853",
                        rtol=1e-10, atol=1e-9, dense_output=True)
        if sol.status != 1:
            raise ValueError("Projectile did not land within the simulated time")
        t_flight = float(sol.t_events[0][0])
        t = np.linspace(0, t_flight, n_points)
        x, y, vx, vy = sol.sol(t)
        y[-1] = 0.0
        end = sol.y_events[0][0]
        result = {
            "range": float(end[0]),
            "max_height": float(max(height, np.max(sol.sol(np.linspace(0, t_flight, 2001))[1]))),
            "flight_time": t_flight,
            "impact_speed": math.hypot(end[2], end[3]),
            "impact_angle_deg": math.degrees(math.atan2(-end[3], end[2])),
            "terminal_velocity": v_term,
        }
        assumptions = [
            "Uniform gravity, flat ground at y = 0",
            "Quadratic drag F = 0.5 rho Cd A v^2 with constant Cd and air density; no wind or lift",
            "Numerical integration (scipy solve_ivp, DOP853)",
        ]

    return {
        "result": result,
        "trajectory": {"t": t.tolist(), "x": np.asarray(x).tolist(), "y": np.asarray(y).tolist()},
        "units": "distances in m, time in s, speeds in m/s, angles in degrees",
        "assumptions": assumptions,
    }


@tool(
    domain="physics",
    name="harmonic_oscillator",
    description=(
        "Mass-spring-damper m x'' + c x' + k x = 0 (simple harmonic if damping=0). Returns natural frequency, "
        "damping ratio, regime (undamped/underdamped/critically damped/overdamped), period, quality factor and "
        "the exact solution x(t), v(t) over duration seconds. Example: mass=1, stiffness=100, damping=2, "
        "initial_displacement=0.1."
    ),
)
def harmonic_oscillator(
    mass: float,
    stiffness: float,
    damping: float = 0.0,
    initial_displacement: float = 1.0,
    initial_velocity: float = 0.0,
    duration: float | None = None,
    n_points: int = 201,
) -> dict:
    if mass <= 0 or stiffness <= 0 or damping < 0:
        raise ValueError("mass and stiffness must be positive and damping >= 0")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    w0 = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))
    if duration is None:
        duration = 5 * 2 * math.pi / w0
    if duration <= 0:
        raise ValueError("duration must be positive")
    x0, v0 = initial_displacement, initial_velocity
    t = np.linspace(0, duration, n_points)

    if math.isclose(zeta, 1.0, rel_tol=1e-9):
        regime = "critically damped"
        a, b = x0, v0 + w0 * x0
        decay = np.exp(-w0 * t)
        x = (a + b * t) * decay
        v = (b - w0 * (a + b * t)) * decay
        wd = None
    elif zeta < 1:
        regime = "undamped" if zeta == 0 else "underdamped"
        wd = w0 * math.sqrt(1 - zeta**2)
        s = zeta * w0
        a, b = x0, (v0 + s * x0) / wd
        decay = np.exp(-s * t)
        cos, sin = np.cos(wd * t), np.sin(wd * t)
        x = decay * (a * cos + b * sin)
        v = decay * ((b * wd - s * a) * cos - (a * wd + s * b) * sin)
    else:
        regime = "overdamped"
        root = w0 * math.sqrt(zeta**2 - 1)
        r1, r2 = -zeta * w0 + root, -zeta * w0 - root
        c2 = (v0 - r1 * x0) / (r2 - r1)
        c1 = x0 - c2
        x = c1 * np.exp(r1 * t) + c2 * np.exp(r2 * t)
        v = c1 * r1 * np.exp(r1 * t) + c2 * r2 * np.exp(r2 * t)
        wd = None

    kinetic, potential = 0.5 * mass * v**2, 0.5 * stiffness * x**2
    energy = kinetic + potential
    return {
        "result": {
            "natural_frequency": w0,
            "natural_frequency_hz": w0 / (2 * math.pi),
            "damping_ratio": zeta,
            "regime": regime,
            "damped_frequency": wd,
            "period": 2 * math.pi / wd if wd else None,
            "quality_factor": 1 / (2 * zeta) if zeta > 0 else None,
            "amplitude": math.sqrt(x0**2 + (v0 / w0) ** 2) if zeta == 0 else None,
        },
        "trajectory": {"t": t.tolist(), "x": x.tolist(), "v": v.tolist(), "energy": energy.tolist(),
                       "kinetic": kinetic.tolist(), "potential": potential.tolist()},
        "units": "frequencies in rad/s (and Hz), period s, displacement m, velocity m/s, energy J",
        "assumptions": ["Linear spring and viscous damping, no external forcing", "Exact analytic solution"],
    }


@tool(
    domain="physics",
    name="pendulum",
    description=(
        "Simple (point-mass) pendulum with the full nonlinear equation theta'' = -(g/L) sin(theta) - (b/m) theta'. "
        "Returns the exact large-amplitude period, the small-angle period, and plot-ready theta(t), omega(t), "
        "bob x/y and energies. Angles in degrees. Example: length=1, initial_angle_deg=60, gravity=9.81."
    ),
)
def pendulum(
    length: float,
    initial_angle_deg: float,
    initial_angular_velocity: float = 0.0,
    mass: float = 1.0,
    gravity: float = G0,
    damping: float = 0.0,
    duration: float | None = None,
    n_points: int = 401,
) -> dict:
    if length <= 0 or mass <= 0 or gravity <= 0 or damping < 0:
        raise ValueError("length, mass and gravity must be positive and damping >= 0")
    if not -180 < initial_angle_deg < 180:
        raise ValueError("initial_angle_deg must be between -180 and 180")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    w0 = math.sqrt(gravity / length)
    t_small = 2 * math.pi / w0
    th0 = math.radians(initial_angle_deg)

    # Amplitude from energy (undamped): 1 - cos(A) = (1 - cos th0) + omega0^2 / (2 w0^2)
    c = 1 - math.cos(th0) + initial_angular_velocity**2 / (2 * w0**2)
    rotating = c >= 2
    if rotating:
        exact_period = None
    else:
        amplitude = math.acos(1 - c)
        exact_period = 4 / w0 * float(ellipk(math.sin(amplitude / 2) ** 2)) if amplitude > 0 else t_small
    if duration is None:
        duration = 4 * (exact_period or t_small)
    if duration <= 0:
        raise ValueError("duration must be positive")

    gamma = damping / mass

    def rhs(_t, s):
        return [s[1], -w0**2 * math.sin(s[0]) - gamma * s[1]]

    t = np.linspace(0, duration, n_points)
    sol = solve_ivp(rhs, (0, duration), [th0, initial_angular_velocity], t_eval=t, method="DOP853",
                    rtol=1e-10, atol=1e-12)
    if not sol.success:
        raise ValueError(f"Integration failed: {sol.message}")
    theta, omega = sol.y
    kinetic = 0.5 * mass * (length * omega) ** 2
    potential = mass * gravity * length * (1 - np.cos(theta))
    return {
        "result": {
            "period": exact_period,
            "small_angle_period": t_small,
            "period_ratio": exact_period / t_small if exact_period else None,
            "natural_frequency": w0,
            "motion": "rotating (goes over the top)" if rotating else "oscillating",
            "max_speed": float(np.max(np.abs(omega)) * length),
        },
        "trajectory": {
            "t": t.tolist(),
            "theta_deg": np.degrees(theta).tolist(),
            "omega": omega.tolist(),
            "x": (length * np.sin(theta)).tolist(),
            "y": (-length * np.cos(theta)).tolist(),
            "kinetic": kinetic.tolist(),
            "potential": potential.tolist(),
        },
        "units": "time s, angles degrees, angular velocity rad/s, positions m (pivot at origin), energy J",
        "assumptions": [
            "Point mass on a massless rigid rod, no air drag except the linear damping term",
            "Exact period from the complete elliptic integral (undamped); numerical solution via solve_ivp",
        ],
    }
