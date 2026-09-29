import numpy as np
import pytest

from app.modules.mathematics.linear_algebra import determinant, eigen, solve_linear_system


def test_solve_2x2():
    r = solve_linear_system([[2, 1], [1, 3]], [3, 5])
    assert r["result"] == pytest.approx([0.8, 1.4])
    assert r["residual_norm"] < 1e-12


def test_solve_3x3():
    # x + y + z = 6, 2y + 5z = -4, 2x + 5y - z = 27  ->  (5, 3, -2)
    r = solve_linear_system([[1, 1, 1], [0, 2, 5], [2, 5, -1]], [6, -4, 27])
    assert r["result"] == pytest.approx([5, 3, -2])


def test_singular_system_rejected():
    with pytest.raises(ValueError, match="singular"):
        solve_linear_system([[1, 2], [2, 4]], [1, 2])


def test_overdetermined_least_squares():
    # Fit y = a + b t through (0,1), (1,3), (2,5): exact line a=1, b=2
    r = solve_linear_system([[1, 0], [1, 1], [1, 2]], [1, 3, 5])
    assert r["result"] == pytest.approx([1, 2])


def test_vector_length_mismatch():
    with pytest.raises(ValueError):
        solve_linear_system([[1, 0], [0, 1]], [1, 2, 3])


def test_eigen_symmetric():
    r = eigen([[2, 1], [1, 2]])
    assert r["result"]["eigenvalues"] == pytest.approx([1, 3])
    assert r["complex"] is False
    a = np.array([[2, 1], [1, 2]])
    for lam, v in zip(r["result"]["eigenvalues"], r["result"]["eigenvectors"]):
        assert a @ np.array(v) == pytest.approx(lam * np.array(v))


def test_eigen_nonsymmetric_real():
    r = eigen([[4, 1], [2, 3]])
    assert r["result"]["eigenvalues"] == pytest.approx([2, 5])


def test_eigen_rotation_complex():
    r = eigen([[0, -1], [1, 0]])
    assert r["complex"] is True
    assert np.allclose(r["result"]["eigenvalues"], [[0, -1], [0, 1]])


def test_eigen_non_square():
    with pytest.raises(ValueError, match="square"):
        eigen([[1, 2, 3], [4, 5, 6]])


def test_determinant():
    assert determinant([[1, 2], [3, 4]])["result"] == pytest.approx(-2)
    assert determinant([[6, 1, 1], [4, -2, 5], [2, 8, 7]])["result"] == pytest.approx(-306)


def test_determinant_ragged_matrix():
    with pytest.raises(ValueError):
        determinant([[1, 2], [3]])
