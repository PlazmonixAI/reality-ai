"""Wave packets, the quantum harmonic oscillator and Rabi oscillations."""
import math

import numpy as np
import pytest

from app.modules.physics.quantum_dynamics import quantum_oscillator, rabi_oscillation, wave_packet

HBAR, ME, EV = 1.054571817e-34, 9.1093837015e-31, 1.602176634e-19


def test_free_packet_moves_at_group_velocity_and_keeps_its_norm():
    r = wave_packet("free", energy_ev=1.0, duration_fs=20)["result"]
    v = math.sqrt(2 * EV / ME) * 1e-6  # m/s to nm per fs, for a 1 eV electron
    assert r["group_velocity_nm_per_fs"] == pytest.approx(v, rel=1e-9)
    assert (r["mean_x_nm"][-1] - r["mean_x_nm"][0]) / 20 == pytest.approx(v, rel=1e-3)
    assert r["final_total"] == pytest.approx(1.0, abs=1e-6)
    assert r["wavelength_nm"] == pytest.approx(1.2264, rel=1e-3)   # de Broglie wavelength of a 1 eV electron


def test_free_packet_spreads_as_theory_says():
    r = wave_packet("free", energy_ev=1.0, packet_width_nm=1.0, duration_fs=30, frames=4)["result"]
    x = np.array(r["x_nm"]) ; d = np.array(r["density_per_nm"][-1])
    d = d / np.trapezoid(d, x)
    mean = np.trapezoid(x * d, x)
    sigma = math.sqrt(np.trapezoid((x - mean) ** 2 * d, x))
    s0 = 1e-9
    expected = math.sqrt(1 + (HBAR * 30e-15 / (2 * ME * s0 ** 2)) ** 2)  # in nm, s0 = 1 nm
    assert sigma == pytest.approx(expected, rel=0.02)


def test_barrier_tunnelling_close_to_plane_wave_value():
    r = wave_packet("barrier", energy_ev=0.5, height_ev=0.6, width_nm=0.6, packet_width_nm=4.0, duration_fs=80)["result"]
    assert r["plane_wave_transmission"] == pytest.approx(0.302, abs=0.002)
    assert r["final_right"] == pytest.approx(r["plane_wave_transmission"], abs=0.03)
    assert r["final_total"] == pytest.approx(1.0, abs=1e-3)


def test_oscillator_levels_and_normalisation():
    q = quantum_oscillator(0.2, 4)["result"]
    assert [l["energy_ev"] for l in q["levels"]] == pytest.approx([0.1, 0.3, 0.5, 0.7, 0.9])
    x = np.array(q["x_nm"])
    for l in q["levels"]:
        assert np.trapezoid(np.array(l["psi"]) ** 2, x) == pytest.approx(1.0, abs=1e-3)
    omega = 0.2 * EV / HBAR
    assert q["period_fs"] == pytest.approx(2 * math.pi / omega * 1e15, rel=1e-9)
    m = q["mean_x_nm"]
    assert m[0] == pytest.approx(-m[len(m) // 2], rel=0.05)  # the superposition swings to the other side in half a period


def test_rabi_oscillation_matches_the_formula():
    r = rabi_oscillation(2.0, 0.0, 1.0, 201)["result"]
    assert r["pi_pulse_us"] == pytest.approx(0.25)
    i = min(range(201), key=lambda k: abs(r["t_us"][k] - 0.25))
    assert r["excited_probability"][i] == pytest.approx(1.0, abs=1e-3)
    d = rabi_oscillation(1.0, 1.0, 3.0)["result"]
    assert max(d["excited_probability"]) == pytest.approx(0.5, abs=1e-3)
    assert all(abs(math.hypot(*b) - 1) < 1e-9 for b in d["bloch"])   # pure state stays on the sphere
