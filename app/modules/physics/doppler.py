"""Doppler effect for sound: moving source and observer, a source driving past a listener, and
the Mach cone of a supersonic source."""
import math

import numpy as np

from app.core.registry import tool


@tool(
    domain="physics",
    name="doppler_effect",
    description=(
        "Doppler effect for sound in still air. Gives the heard frequency while the source approaches and recedes "
        "(source_speed, observer_speed in m/s, positive = moving toward the other), the Mach number and Mach-cone "
        "angle, and a drive-by: the source passes a listener at closest distance pass_distance (m); returns the "
        "heard frequency vs arrival time and the emission points of wavefronts for animation. "
        "Example: frequency=440, source_speed=30."
    ),
)
def doppler_effect(
    frequency: float,
    source_speed: float,
    observer_speed: float = 0.0,
    sound_speed: float = 343.0,
    pass_distance: float = 20.0,
    track_half_length: float = 200.0,
    n_points: int = 600,
    n_wavefronts: int = 40,
) -> dict:
    if frequency <= 0 or sound_speed <= 0:
        raise ValueError("frequency and sound_speed must be positive")
    if source_speed < 0 or observer_speed < 0:
        raise ValueError("speeds are magnitudes (>= 0); approach and recession are both reported")
    if observer_speed >= sound_speed:
        raise ValueError("observer_speed must be below the speed of sound")
    if pass_distance <= 0 or track_half_length <= 0:
        raise ValueError("pass_distance and track_half_length must be positive")
    if not 10 <= n_points <= 20_000 or not 1 <= n_wavefronts <= 500:
        raise ValueError("n_points must be 10..20000 and n_wavefronts 1..500")
    c, vs, vo = sound_speed, source_speed, observer_speed
    mach = vs / c
    approach = frequency * (c + vo) / (c - vs) if vs < c else None
    recede = frequency * (c - vo) / (c + vs)

    # Drive-by: source along x from -L to +L at speed vs, listener at rest at (0, d)
    if vs > 0:
        duration = 2 * track_half_length / vs
        te = np.linspace(0, duration, n_points)
        xs = -track_half_length + vs * te
        dist = np.hypot(xs, pass_distance)
        t_arrive = te + dist / c
        v_toward = vs * (-xs) / dist  # radial velocity component toward the listener
        # |1 − v_r/c|: a supersonic source's approach sound arrives time-reversed (negative denominator)
        heard = frequency / np.abs(1 - v_toward / c)
        # Supersonic: arrival time has a minimum (the boom). Emissions before it are heard in reverse order.
        k_boom = int(np.argmin(t_arrive))
        emit_t = np.linspace(0, duration, n_wavefronts)
        emit_x = -track_half_length + vs * emit_t
        drive_by = {
            "emission_time": te.tolist(), "source_x": xs.tolist(), "arrival_time": t_arrive.tolist(),
            "heard_frequency": heard.tolist(),
            "wavefronts": {"time": emit_t.tolist(), "x": emit_x.tolist()},
            "duration": duration,
            "boom_time": float(t_arrive[k_boom]) if vs > c else None,
            "boom_index": k_boom if vs > c else None,
        }
    else:
        drive_by = None
    return {
        "result": {
            "approaching_frequency": approach,
            "receding_frequency": recede,
            "pitch_drop_ratio": approach / recede if approach else None,
            "pitch_drop_semitones": 12 * math.log2(approach / recede) if approach else None,
            "mach_number": mach,
            "supersonic": vs > c,
            "mach_cone_half_angle_deg": math.degrees(math.asin(c / vs)) if vs > c else None,
            "wavelength_ahead": (c - vs) / frequency if vs < c else None,
            "wavelength_behind": (c + vs) / frequency,
        },
        "drive_by": drive_by,
        "units": "frequencies in Hz, speeds in m/s, wavelengths in m, times in s, angles in degrees",
        "assumptions": ["Still, uniform air; straight-line source motion at constant speed",
                        "Classical (non-relativistic) Doppler formula f' = f (c + v_o)/(c − v_s)",
                        "Drive-by listener at rest; supersonic sources are heard only after the cone passes"],
    }
