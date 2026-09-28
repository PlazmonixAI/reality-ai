"""Safe-ish parsing of user-supplied math expressions into sympy objects.

sympy's string parser evaluates Python, so input from the API is screened
first: no attribute access, no dunders, no builtins, bounded length.
"""
import re

import sympy as sp
from tokenize import TokenError
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

MAX_EXPRESSION_LENGTH = 1000
_FORBIDDEN = re.compile(r"__|\.\s*[A-Za-z_]|\blambda\b|[;`\\]|\bimport\b")
_TRANSFORMS = standard_transformations + (implicit_multiplication, convert_xor)
# Only these names mean something special; every other name becomes a plain
# symbol, so variables like N, S, Q or gamma are never hijacked by sympy.
_FUNCTIONS = (
    "sin cos tan cot sec csc asin acos atan atan2 acot sinh cosh tanh asinh acosh atanh "
    "exp log sqrt cbrt root Abs sign floor ceiling factorial binomial erf erfc "
    "Heaviside DiracDelta Min Max"
).split()
_GLOBALS: dict = {name: getattr(sp, name) for name in _FUNCTIONS}
_GLOBALS.update({
    "ln": sp.log, "abs": sp.Abs,
    "pi": sp.pi, "E": sp.E, "I": sp.I, "oo": sp.oo, "inf": sp.oo,
    # Constructors emitted by sympy's parser itself.
    "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational,
    "Symbol": sp.Symbol, "Function": sp.Function,
    "__builtins__": {},
})


def parse_expression(text: str) -> sp.Expr:
    """Parse a math expression string (e.g. 'sin(x)*exp(-x^2)') into sympy.

    Raises ValueError for anything that is not a plain math expression.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Expression must be a non-empty string")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ValueError(f"Expression longer than {MAX_EXPRESSION_LENGTH} characters")
    if _FORBIDDEN.search(text):
        raise ValueError(f"Expression contains forbidden syntax: {text!r}")
    try:
        return parse_expr(text, global_dict=dict(_GLOBALS), transformations=_TRANSFORMS)
    except TokenError:
        raise ValueError(f"Could not parse expression {text!r}: unbalanced brackets or an incomplete expression") from None
    except (SyntaxError, TypeError, NameError, AttributeError, sp.SympifyError) as e:
        raise ValueError(f"Could not parse expression {text!r}: {e}") from e


def parse_equation(text: str) -> sp.Expr:
    """Parse 'lhs = rhs' (or a bare expression meaning expr = 0) into lhs - rhs."""
    if "=" in text:
        lhs, rhs = text.split("=", 1)
        return parse_expression(lhs) - parse_expression(rhs)
    return parse_expression(text)


def parse_point(value: str | float | int) -> sp.Expr:
    """Parse a numeric point such as 0, 2.5, 'pi/2', 'oo' or '-oo'."""
    if isinstance(value, (int, float)):
        return sp.nsimplify(value) if isinstance(value, int) else sp.Float(value)
    return parse_expression(str(value))


def symbol(name: str) -> sp.Symbol:
    """Validate a variable name and return its sympy Symbol."""
    if not isinstance(name, str) or not name.isidentifier() or name.startswith("_"):
        raise ValueError(f"Invalid variable name: {name!r}")
    return sp.Symbol(name)
