from __future__ import annotations

import re
from difflib import get_close_matches
from math import log

import sympy as _sympy
from sympy import (
    Abs,
    Add,
    Dummy,
    E,
    Eq,
    Float,
    Function,
    Integer,
    Matrix,
    Mul,
    N,
    Pow,
    Rational,
    Symbol,
    cos,
    diff,
    dsolve,
    eye,
    exp,
    factorial,
    factorint,
    gcd,
    integrate,
    isprime,
    lcm,
    linsolve,
    log,
    ones,
    pi,
    simplify,
    sin,
    solve,
    sqrt,
    symbols,
    tan,
    zeros,
    preorder_traversal,
)
from sympy.parsing.sympy_parser import (
    auto_number,
    convert_xor,
    factorial_notation,
    function_exponentiation,
    implicit_multiplication_application,
    parse_expr,
    rationalize,
)

x, y, z, t = symbols("x y z t")
f = Function("f")
yf = Function("y")


def _infer_variable(expr, op_name: str):
    free_symbols = sorted(expr.free_symbols, key=str)
    if len(free_symbols) == 1:
        return free_symbols[0]
    if not free_symbols:
        raise ValueError(f"{op_name} requires a variable (no symbols found)")
    raise ValueError(f"ambiguous variable for {op_name}; pass one explicitly")


def _d(expr, var=None):
    if var is None:
        var = _infer_variable(expr, "d(expr)")
    return diff(expr, var)


def _int(expr, var=None):
    if var is None:
        var = _infer_variable(expr, "int(expr)")
    return integrate(expr, var)


def _num(expr):
    return expr.as_numer_denom()[0]


def _den(expr):
    return expr.as_numer_denom()[1]


LOCALS_DICT = {
    "x": x,
    "y": y,
    "z": z,
    "t": t,
    "pi": pi,
    "e": E,
    "f": f,
    "yf": yf,
    "d": _d,
    "int": _int,
    "gcd": gcd,
    "lcm": lcm,
    "isprime": isprime,
    "factorint": factorint,
    "num": _num,
    "den": _den,
    "solve": solve,
    "dsolve": dsolve,
    "Eq": Eq,
    "N": N,
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "exp": exp,
    "log": log,
    "sqrt": sqrt,
    "abs": Abs,
    "Matrix": Matrix,
    "eye": eye,
    "zeros": zeros,
    "ones": ones,
    "det": lambda matrix: matrix.det(),
    "inv": lambda matrix: matrix.inv(),
    "rank": lambda matrix: matrix.rank(),
    "eigvals": lambda matrix: matrix.eigenvals(),
    "rref": lambda matrix: matrix.rref(),
    "nullspace": lambda matrix: matrix.nullspace(),
    "msolve": lambda matrix, rhs: matrix.LUsolve(rhs),
    "linsolve": linsolve,
    "symbols": symbols,
    "S": Symbol,
}

SYMPY_EXTRA_ALLOWLIST = (
    "S",
    "acos",
    "acosh",
    "apart",
    "asin",
    "asinh",
    "atan",
    "atanh",
    "binomial",
    "cancel",
    "collect",
    "cosh",
    "cot",
    "csc",
    "expand",
    "factor",
    "gamma",
    "limit",
    "powsimp",
    "product",
    "sec",
    "series",
    "sinh",
    "summation",
    "tanh",
    "together",
    "trigsimp",
)


def _expanded_sympy_locals() -> dict[str, object]:
    expanded: dict[str, object] = {}
    for name in SYMPY_EXTRA_ALLOWLIST:
        if name in LOCALS_DICT:
            continue
        if not name.isidentifier() or name.startswith("_"):
            continue
        value = getattr(_sympy, name, None)
        if value is None or not callable(value):
            continue
        expanded[name] = value
    return expanded


LOCALS_DICT.update(_expanded_sympy_locals())


# parse_expr internally uses eval. Keep globals minimal and disable builtins.
GLOBAL_DICT = {
    "__builtins__": {},
    "Add": Add,
    "Integer": Integer,
    "Float": Float,
    "Mul": Mul,
    "Pow": Pow,
    "Rational": Rational,
    "Symbol": Symbol,
    "factorial": factorial,
}

TRANSFORMS = (auto_number, factorial_notation, convert_xor, function_exponentiation, rationalize)
RELAXED_TRANSFORMS = (
    auto_number,
    factorial_notation,
    convert_xor,
    function_exponentiation,
    implicit_multiplication_application,
    rationalize,
)
MAX_EXPRESSION_CHARS = 2000
BLOCKED_PATTERN = re.compile(r"(__|;|\n|\r)")
ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)\s*$")
EQUALITY_PATTERN = re.compile(r"(?<![<>=!])=(?!=)")
LEIBNIZ_SIMPLE_PATTERN = re.compile(
    r"\bd\s*([A-Za-z][A-Za-z0-9_]*(?:\([^()]*\))?)\s*/\s*d\s*([A-Za-z][A-Za-z0-9_]*)\b"
)
ODE_SHORT_EQ_PATTERN = re.compile(
    r"^\s*d\s*([A-Za-z][A-Za-z0-9_]*)\s*/\s*d\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$"
)
LATEX_LEIBNIZ_PATTERN = re.compile(
    r"\\frac\s*\{\s*d\s*([A-Za-z][A-Za-z0-9_]*)\s*\}\s*\{\s*d\s*([A-Za-z][A-Za-z0-9_]*)\s*\}"
)
LATEX_HIGHER_LEIBNIZ_PATTERN = re.compile(
    r"\\frac\s*\{\s*d\^([2-9])\s*([A-Za-z][A-Za-z0-9_]*)\s*\}\s*\{\s*d\s*([A-Za-z][A-Za-z0-9_]*)\s*\^\s*\1\s*\}"
)
LATEX_FRAC_PATTERN = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
LATEX_SQRT_PATTERN = re.compile(r"\\sqrt\s*\{([^{}]+)\}")
PRIME_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*('{1,4})")
PRIME_AT_POINT_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*('{1,4})\s*\(\s*([^()]+?)\s*\)")
BARE_FUNC_ARG_PATTERN = re.compile(r"\b(sin|cos|tan)([xyzt])\b")
MAX_INTEGER_POWER_EXP = 1_000_000
MAX_FACTORIAL_N = 100_000
FACTORIAL_LITERAL_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:\(\s*)?(\d+)(?:\s*\))?\s*!")
FACTORIAL_CALL_LITERAL_PATTERN = re.compile(r"\bfactorial\s*\(\s*(\d+)\s*\)")


def _dependent_expr(dep: str, var: str) -> str:
    if dep == "y":
        return f"yf({var})"
    if dep == "f":
        return f"f({var})"
    return dep


def _replace_bare_dependent(
    rhs: str,
    dep: str,
    dep_expr: str,
    *,
    add_implicit_mul: bool = True,
) -> str:
    pattern = re.compile(
        rf"(?<![A-Za-z_]){re.escape(dep)}(?![A-Za-z0-9_]|(?:\s*\())"
    )

    def repl(match: re.Match[str]) -> str:
        if (
            add_implicit_mul
            and match.start() > 0
            and (rhs[match.start() - 1].isalnum() or rhs[match.start() - 1] == ")")
        ):
            return f"*{dep_expr}"
        return dep_expr

    return pattern.sub(repl, rhs)


def _strip_outer_wrappers(text: str) -> str:
    out = text.strip()
    while True:
        before = out
        if len(out) >= 2 and out[0] == out[-1] and out[0] in {"'", '"'}:
            out = out[1:-1].strip()
        elif out.startswith("$$") and out.endswith("$$") and len(out) >= 4:
            out = out[2:-2].strip()
        elif out.startswith("$") and out.endswith("$") and len(out) >= 2:
            out = out[1:-1].strip()
        elif out.startswith(r"\(") and out.endswith(r"\)"):
            out = out[2:-2].strip()
        elif out.startswith(r"\[") and out.endswith(r"\]"):
            out = out[2:-2].strip()
        if out == before:
            return out


def _nth_derivative(dep: str, var: str, order: int) -> str:
    out = _dependent_expr(dep, var)
    for _ in range(order):
        out = f"d({out}, {var})"
    return out


def _replace_latex_notation(text: str) -> str:
    out = text
    out = LATEX_HIGHER_LEIBNIZ_PATTERN.sub(
        lambda m: _nth_derivative(m.group(2), m.group(3), int(m.group(1))),
        out,
    )
    out = LATEX_LEIBNIZ_PATTERN.sub(lambda m: f"d{m.group(1)}/d{m.group(2)}", out)
    while True:
        updated = LATEX_FRAC_PATTERN.sub(r"(\1)/(\2)", out)
        if updated == out:
            break
        out = updated
    out = LATEX_SQRT_PATTERN.sub(r"sqrt(\1)", out)
    out = re.sub(r"\\(sin|cos|tan|ln|log|exp)\b", r"\1", out)
    out = re.sub(r"\\pi\b", "pi", out)
    out = out.replace(r"\cdot", "*").replace(r"\times", "*")
    return out


def _replace_prime_notation(text: str) -> str:
    return PRIME_PATTERN.sub(
        lambda m: _nth_derivative(m.group(1), "x", len(m.group(2))),
        text,
    )


def _replace_prime_at_point_notation(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        dep = match.group(1)
        order = len(match.group(2))
        at = match.group(3).strip()
        derivative = _nth_derivative(dep, "x", order)
        if at == "x":
            return derivative
        return f"{derivative}.subs(x, {at})"

    return PRIME_AT_POINT_PATTERN.sub(repl, text)


def _normalize_bare_function_shorthand(
    text: str, *, relaxed: bool
) -> tuple[str, list[tuple[str, str]]]:
    if not relaxed:
        return text, []

    rewrites: list[tuple[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        original = match.group(0)
        rewritten = f"{match.group(1)}({match.group(2)})"
        rewrites.append((original, rewritten))
        return rewritten

    normalized = BARE_FUNC_ARG_PATTERN.sub(repl, text)
    return normalized, rewrites


def relaxed_function_rewrites(expression: str) -> list[tuple[str, str]]:
    normalized = _strip_outer_wrappers(expression)
    normalized = normalized.replace("−", "-")
    normalized = _replace_latex_notation(normalized)
    normalized = normalized.replace("{", "(").replace("}", ")")
    normalized = re.sub(r"\bln\s*\(", "log(", normalized)
    _, rewrites = _normalize_bare_function_shorthand(normalized, relaxed=True)
    return rewrites


def reserved_name_suggestion(
    name: str, session_locals: dict | None = None
) -> str | None:
    if not session_locals:
        return None
    prefix_matches = sorted(
        k for k in session_locals if k.startswith(name) and k != name
    )
    if prefix_matches:
        return prefix_matches[0]
    matches = get_close_matches(name, list(session_locals.keys()), n=1, cutoff=0.75)
    if not matches:
        return None
    return matches[0]


def _normalize_ode_equation_dependents(text: str, *, relaxed: bool) -> str:
    out = text
    if not EQUALITY_PATTERN.search(out):
        return out
    if re.search(r"\bd\s*\(\s*(?:yf\s*\(|y\b)", out):
        out = _replace_bare_dependent(out, "y", "yf(x)", add_implicit_mul=relaxed)
    if re.search(r"\bd\s*\(\s*f\s*\(", out):
        out = _replace_bare_dependent(out, "f", "f(x)", add_implicit_mul=relaxed)
    return out


def _validate_expression(expression: str) -> None:
    if not expression.strip():
        raise ValueError("empty expression")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ValueError(f"expression too long (max {MAX_EXPRESSION_CHARS} chars)")
    if BLOCKED_PATTERN.search(expression):
        raise ValueError("blocked token in expression")


def normalize_expression(expression: str, relaxed: bool = False) -> str:
    normalized = _strip_outer_wrappers(expression)
    normalized = normalized.replace("−", "-")
    normalized = _replace_latex_notation(normalized)
    normalized = normalized.replace("{", "(").replace("}", ")")
    # Accept common math shorthand from CAS/calculator input style.
    normalized = re.sub(r"\bln\s*\(", "log(", normalized)
    normalized, _ = _normalize_bare_function_shorthand(normalized, relaxed=relaxed)
    normalized = _replace_prime_at_point_notation(normalized)
    normalized = _replace_prime_notation(normalized)
    # Treat y(x) as an ODE function call while keeping y available as a symbol.
    normalized = re.sub(r"\by\s*\(", "yf(", normalized)
    ode_match = ODE_SHORT_EQ_PATTERN.match(normalized)
    if ode_match:
        dep, var, rhs = ode_match.group(1), ode_match.group(2), ode_match.group(3)
        dep_expr = _dependent_expr(dep, var)
        rhs = _replace_bare_dependent(rhs, dep, dep_expr, add_implicit_mul=relaxed)
        return f"Eq(d({dep_expr}, {var}), {rhs})"
    # Support Leibniz-style shorthand: d(expr)/dvar -> d(expr, var)
    normalized = re.sub(
        r"\bd\s*\((.+?)\)\s*/\s*d\s*([A-Za-z][A-Za-z0-9_]*)\b",
        r"d(\1, \2)",
        normalized,
    )
    normalized = LEIBNIZ_SIMPLE_PATTERN.sub(
        lambda m: f"d({_dependent_expr(m.group(1), m.group(2))}, {m.group(2)})",
        normalized,
    )
    normalized = _normalize_ode_equation_dependents(normalized, relaxed=relaxed)
    if EQUALITY_PATTERN.search(normalized) and not ASSIGNMENT_PATTERN.match(normalized):
        lhs, rhs = EQUALITY_PATTERN.split(normalized, maxsplit=1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        if lhs and rhs:
            normalized = f"Eq({lhs}, {rhs})"
    return normalized


def _evaluate_parsed(parsed, simplify_output: bool):
    if isinstance(parsed, (list, tuple, dict)):
        return parsed
    if simplify_output:
        return simplify(parsed)
    return parsed


def _is_huge_integer_power(node) -> bool:
    if not isinstance(node, Pow):
        return False
    if not (node.base.is_Integer and node.exp.is_Integer):
        if not node.base.is_Integer:
            return False
    exp_value = _integer_value_capped(node.exp, cap=MAX_INTEGER_POWER_EXP)
    if exp_value is None:
        return False
    return abs(exp_value) > MAX_INTEGER_POWER_EXP


def _pow_capped(base: int, exp: int, cap: int) -> int | None:
    if exp < 0:
        return None
    if base in {-1, 0, 1}:
        return pow(base, exp)
    if exp == 0:
        return 1
    # Fast magnitude check to avoid materializing huge intermediates.
    if exp * log(abs(base)) > log(cap + 1):
        return cap + 1
    value = pow(base, exp)
    if abs(value) > cap:
        return cap + 1
    return value


def _integer_value_capped(node, *, cap: int) -> int | None:
    if isinstance(node, Integer):
        value = int(node)
        if abs(value) > cap:
            return cap + 1 if value > 0 else -(cap + 1)
        return value
    if isinstance(node, Pow):
        base_value = _integer_value_capped(node.base, cap=cap)
        exp_value = _integer_value_capped(node.exp, cap=cap)
        if base_value is None or exp_value is None:
            return None
        return _pow_capped(base_value, exp_value, cap)
    return None


def _validate_factorial_literals(expr: str) -> None:
    for pattern in (FACTORIAL_LITERAL_PATTERN, FACTORIAL_CALL_LITERAL_PATTERN):
        for match in pattern.finditer(expr):
            n = int(match.group(1))
            if n > MAX_FACTORIAL_N:
                raise ValueError(
                    f"factorial input too large to evaluate exactly (max n {MAX_FACTORIAL_N})"
                )


def _raise_if_huge_factorial_call(parsed) -> None:
    if not hasattr(parsed, "args"):
        return
    for node in preorder_traversal(parsed):
        if getattr(node, "func", None) != factorial or not getattr(node, "args", ()):
            continue
        n_value = _integer_value_capped(node.args[0], cap=MAX_FACTORIAL_N)
        if n_value is not None and n_value > MAX_FACTORIAL_N:
            raise ValueError(
                f"factorial input too large to evaluate exactly (max n {MAX_FACTORIAL_N})"
            )


def _reduce_huge_integer_powers(parsed):
    if not hasattr(parsed, "atoms"):
        return None
    huge_powers = sorted((p for p in parsed.atoms(Pow) if _is_huge_integer_power(p)), key=str)
    if not huge_powers:
        return None

    placeholders = {pow_expr: Dummy(f"_phil_huge_pow_{i}") for i, pow_expr in enumerate(huge_powers)}
    reduced = simplify(parsed.xreplace(placeholders))
    if any(placeholder in reduced.free_symbols for placeholder in placeholders.values()):
        raise ValueError(
            f"integer power too large to evaluate exactly (max exponent {MAX_INTEGER_POWER_EXP})"
        )
    return reduced


def _parse_with_guardrails(expr: str, *, local_dict, transformations):
    _validate_factorial_literals(expr)
    # Parse safely first so huge integer powers stay symbolic and can be reduced
    # before any eager bigint materialization.
    parsed_safe = parse_expr(
        expr,
        local_dict=local_dict,
        global_dict=GLOBAL_DICT,
        transformations=transformations,
        evaluate=False,
    )
    _raise_if_huge_factorial_call(parsed_safe)
    reduced = _reduce_huge_integer_powers(parsed_safe)
    if reduced is not None:
        return reduced

    return parse_expr(
        expr,
        local_dict=local_dict,
        global_dict=GLOBAL_DICT,
        transformations=transformations,
        evaluate=True,
    )


def evaluate(
    expression: str,
    relaxed: bool = False,
    session_locals: dict | None = None,
    simplify_output: bool = True,
):
    _validate_expression(expression)
    normalized = normalize_expression(expression, relaxed=relaxed)
    transforms = RELAXED_TRANSFORMS if relaxed else TRANSFORMS
    local_dict = dict(LOCALS_DICT)
    if session_locals:
        local_dict.update(session_locals)

    match = ASSIGNMENT_PATTERN.match(normalized)
    if match:
        name, rhs = match.group(1), match.group(2)
        if name in LOCALS_DICT:
            raise ValueError(f"cannot assign reserved name: {name}")
        parsed_rhs = _parse_with_guardrails(
            rhs,
            local_dict=local_dict,
            transformations=transforms,
        )
        result = _evaluate_parsed(parsed_rhs, simplify_output=simplify_output)
        if session_locals is not None:
            session_locals[name] = result
            session_locals["ans"] = result
        return result

    parsed = _parse_with_guardrails(
        normalized,
        local_dict=local_dict,
        transformations=transforms,
    )
    result = _evaluate_parsed(parsed, simplify_output=simplify_output)
    if session_locals is not None:
        session_locals["ans"] = result
    return result
