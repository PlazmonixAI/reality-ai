"""Reference example tool. Copy this pattern for every new tool."""
import sympy as sp

from app.core.registry import tool


@tool(
    domain="mathematics",
    name="solve_equation",
    description="Solve an algebraic equation for a variable. Example: equation='x**2 - 4 = 0', variable='x'.",
)
def solve_equation(equation: str, variable: str = "x") -> dict:
    var = sp.Symbol(variable)
    if "=" in equation:
        lhs, rhs = equation.split("=", 1)
        expr = sp.sympify(lhs) - sp.sympify(rhs)
    else:
        expr = sp.sympify(equation)
    solutions = sp.solve(expr, var)
    return {
        "result": [str(s) for s in solutions],
        "units": "dimensionless",
        "assumptions": ["Symbolic solution over the complex numbers (sympy.solve)"],
    }
