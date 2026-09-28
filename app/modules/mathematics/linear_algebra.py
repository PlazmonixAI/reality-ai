"""Numerical linear algebra: linear systems, eigen-decomposition, determinants (numpy)."""
import numpy as np

from app.core.registry import tool


def _matrix(matrix: list[list[float]], square: bool = True) -> np.ndarray:
    try:
        a = np.array(matrix, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Matrix must be a rectangular list of number rows: {e}") from e
    if a.ndim != 2 or a.size == 0:
        raise ValueError("Matrix must be a non-empty 2-D list, e.g. [[1, 2], [3, 4]]")
    if square and a.shape[0] != a.shape[1]:
        raise ValueError(f"Matrix must be square, got shape {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError("Matrix entries must be finite numbers")
    return a


def _clean(values: np.ndarray) -> tuple[list, bool]:
    """Real list if imaginary parts are negligible, else list of [re, im] pairs."""
    if np.allclose(np.imag(values), 0, atol=1e-12):
        return np.real(values).tolist(), False
    return np.stack([np.real(values), np.imag(values)], axis=-1).tolist(), True


@tool(
    domain="mathematics",
    name="solve_linear_system",
    description=(
        "Solve A x = b. matrix=A as a list of rows, vector=b. Square non-singular systems are solved exactly; "
        "non-square systems return the least-squares solution. Example: matrix=[[2,1],[1,3]], vector=[3,5]."
    ),
)
def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> dict:
    a = _matrix(matrix, square=False)
    b = np.array(vector, dtype=float)
    if b.shape != (a.shape[0],):
        raise ValueError(f"vector must have {a.shape[0]} entries to match the matrix rows")

    rank = int(np.linalg.matrix_rank(a))
    if a.shape[0] == a.shape[1] and rank == a.shape[0]:
        x = np.linalg.solve(a, b)
        method = "Exact solve via LU decomposition (numpy.linalg.solve)"
    elif a.shape[0] == a.shape[1]:
        raise ValueError(f"Matrix is singular (rank {rank} < {a.shape[0]}); no unique solution")
    else:
        x = np.linalg.lstsq(a, b, rcond=None)[0]
        method = "Least-squares solution (numpy.linalg.lstsq) for a non-square system"
    residual = float(np.linalg.norm(a @ x - b))
    return {
        "result": x.tolist(),
        "residual_norm": residual,
        "rank": rank,
        "units": "units of b / units of A",
        "assumptions": [method, "Floating-point (double precision) arithmetic"],
    }


@tool(
    domain="mathematics",
    name="eigen",
    description=(
        "Eigenvalues and eigenvectors of a square matrix. Complex values are returned as [re, im] pairs. "
        "Example: matrix=[[2,0],[0,3]]."
    ),
)
def eigen(matrix: list[list[float]]) -> dict:
    a = _matrix(matrix)
    symmetric = np.allclose(a, a.T)
    if symmetric:
        values, vectors = np.linalg.eigh(a)
    else:
        values, vectors = np.linalg.eig(a)
        order = np.lexsort((np.imag(values), np.real(values)))
        values, vectors = values[order], vectors[:, order]
    eigenvalues, complex_values = _clean(values)
    # Each eigenvector is a column; return them as a list, one per eigenvalue.
    eigenvectors, complex_vectors = _clean(vectors.T)
    return {
        "result": {"eigenvalues": eigenvalues, "eigenvectors": eigenvectors},
        "complex": complex_values or complex_vectors,
        "units": "eigenvalues in units of the matrix entries; eigenvectors unit-normalised",
        "assumptions": [
            "Symmetric matrix: numpy.linalg.eigh, eigenvalues ascending" if symmetric
            else "General matrix: numpy.linalg.eig, eigenvalues sorted by real part",
            "Eigenvectors normalised to unit length (sign is arbitrary)",
        ],
    }


@tool(
    domain="mathematics",
    name="determinant",
    description="Determinant of a square matrix. Example: matrix=[[1,2],[3,4]] -> -2.",
)
def determinant(matrix: list[list[float]]) -> dict:
    a = _matrix(matrix)
    return {
        "result": float(np.linalg.det(a)),
        "units": "units of the matrix entries ^ n",
        "assumptions": ["Computed via LU decomposition (numpy.linalg.det); floating-point rounding applies"],
    }
