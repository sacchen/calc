from __future__ import annotations

import re

from .core import normalize_expression, relaxed_function_rewrites, reserved_name_suggestion

FALLBACK_HINT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"unterminated string literal|eol while scanning string literal|unterminated string"),
        "check quote balance: close every ' or \" in the expression",
    ),
    (
        re.compile(r"eof in multi-line statement|unexpected eof while parsing"),
        "check missing closing ')' or unmatched quote",
    ),
    (
        re.compile(r"unexpected character after line continuation character"),
        "remove stray backslashes; enter plain math syntax",
    ),
    (
        re.compile(r"tokenerror"),
        "check expression syntax near the end; try :examples for working patterns",
    ),
)


def should_print_wolfram_hint(exc: Exception) -> bool:
    text = str(exc).lower()
    if "cannot assign reserved name" in text:
        return False
    if "integer power too large to evaluate exactly" in text:
        return False
    if "factorial input too large to evaluate exactly" in text:
        return False
    if "int_max_str_digits" in text:
        return False
    return True


def parse_explanation(expr: str, relaxed: bool, enabled: bool) -> str | None:
    if not enabled:
        return None
    normalized = normalize_expression(expr, relaxed=relaxed)
    message = f"parsed as: {normalized}"
    compact = re.sub(r"\s+", "", expr)
    if re.match(r"^-[A-Za-z0-9_)]+(?:\^|\*\*)", compact):
        message += " | precedence: -a^b means -(a^b); use (-a)^b for a negative base"
    return message


def relaxed_rewrite_messages(expr: str, relaxed: bool) -> list[str]:
    if not relaxed:
        return []
    seen: set[tuple[str, str]] = set()
    messages: list[str] = []
    for original, rewritten in relaxed_function_rewrites(expr):
        if (original, rewritten) in seen:
            continue
        seen.add((original, rewritten))
        messages.append(f"interpreted '{original}' as '{rewritten}'")
    return messages


def eq_has_top_level_comma(expr: str) -> bool:
    stripped = expr.strip()
    if not stripped.startswith("Eq("):
        return True
    inner = stripped[3:]
    if inner.endswith(")"):
        inner = inner[:-1]
    depth = 0
    for ch in inner:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return True
    return False


def _suggest_strict_ode_multiplication(expr: str) -> str:
    # In strict mode, users must write explicit multiplication for ODE shorthand.
    fixed = re.sub(r"(?<=[0-9)])\s+(?=[A-Za-z(])", "*", expr)
    fixed = re.sub(r"(?<=[0-9)])(?=[A-Za-z(])", "*", fixed)
    return fixed


def hint_for_error(message: str, expr: str | None = None, session_locals: dict | None = None) -> str | None:
    text = message.lower()
    compact_expr = re.sub(r"\s+", "", expr).lower() if expr else ""

    if compact_expr.startswith("gcd("):
        if "takes 2 arguments or a sequence of arguments" in text or "positional argument" in text:
            return "gcd syntax: gcd(a, b) (for example gcd(8, 12))"
    if compact_expr.startswith("lcm("):
        if "takes 2 arguments or a sequence of arguments" in text or "positional argument" in text:
            return "lcm syntax: lcm(a, b) (for example lcm(8, 12))"
    if compact_expr.startswith("isprime("):
        if "is not an integer" in text:
            return "isprime expects an integer n (for example isprime(101))"
        if "positional argument" in text:
            return "isprime syntax: isprime(n)"
    if compact_expr.startswith("factorint("):
        if "is not an integer" in text:
            return "factorint expects an integer n (for example factorint(84))"
        if "positional argument" in text:
            return "factorint syntax: factorint(n)"
    if compact_expr.startswith("num("):
        if "missing 1 required positional argument" in text or "positional argument" in text:
            return "num syntax: num(expr) (for example num(3/14))"
    if compact_expr.startswith("den("):
        if "missing 1 required positional argument" in text or "positional argument" in text:
            return "den syntax: den(expr) (for example den(3/14))"

    if text.startswith("linalg ") or text.startswith("unknown linalg "):
        return "linalg syntax: 'linalg solve A=[[...]] b=[...]' or 'linalg rref A=[[...]]'; use :linalg"
    if "unexpected eof" in text:
        if expr and ("/d" in expr or expr.strip().startswith("d(")):
            return "derivative syntax: d(expr, var) or d(sin(x))/dx or df(t)/dt"
        return "check missing closing ')' or unmatched quote"
    if "invalid syntax" in text:
        if expr:
            compact = re.sub(r"\s+", "", expr)
            if re.search(r"\b(?:sin|cos|tan)\s+[A-Za-z0-9_]+\s*(?:\^|\*\*)", expr):
                return "ambiguous trig shorthand: use sin(x^2) or (sin(x))^2 explicitly"
            if re.search(r"\bode\b", expr, flags=re.IGNORECASE):
                suggested = _suggest_strict_ode_multiplication(expr)
                if suggested != expr:
                    return (
                        "use explicit multiplication in ODEs (e.g. 20*y); "
                        f"try: {suggested} ; or run without --strict"
                    )
            if expr.strip().startswith("Eq(") and not eq_has_top_level_comma(expr):
                return "Eq syntax: Eq(lhs, rhs), for example Eq(d(y(x), x), y(x))"
            if "dsolve(" in compact and "eq(" not in compact:
                return "dsolve expects an equation: use dsolve(Eq(...), y(x))"
            if "\\frac" in expr:
                return "LaTeX fraction syntax: \\frac{numerator}{denominator}"
            if "d(" in compact or re.search(r"\bd[A-Za-z0-9_]+/d[A-Za-z0-9_]+\b", compact):
                return "derivative syntax: d(expr, var) or d(sin(x))/dx or df(t)/dt"
            if "matrix(" in compact.lower():
                return "matrix syntax: Matrix([[1,2],[3,4]])"
        return "check commas and brackets; try :examples for working patterns"
    if "cannot assign reserved name:" in text:
        if "cannot assign reserved name: f" in text:
            suggestion = reserved_name_suggestion("f", session_locals=session_locals)
            if suggestion:
                return f"'f' is reserved for function notation in ODEs; try '{suggestion}'"
            return "'f' is reserved for function notation in ODEs; choose another variable name (e.g. ff)"
        return "that name is reserved by phil internals; choose a different variable name"
    if "name '" in text and "is not defined" in text:
        missing = re.search(r"name '([^']+)' is not defined", message)
        missing_name = missing.group(1) if missing else None
        if missing_name and missing_name.isalpha() and missing_name[0].isupper():
            return "for symbolic coefficients, use inline names like S('A'), S('B'), S('C')"
        if expr and ("/d" in expr or expr.strip().startswith("d")):
            return "derivative syntax: d(expr, var) or d(sin(x))/dx or df(t)/dt"
        return "use one of: x y z t pi e f, plus helper functions like symbols(...)"
    if "dsolve() and classify_ode() only work with functions of one variable" in text:
        return "for ODEs, use function notation: y(x) and dsolve(Eq(d(y(x), x), ...), y(x))"
    if "mixed dependent variable notation" in text:
        return "in ODE input, use one dependent form consistently (y with y'/dy/dx, or explicit y(x))"
    if "initial condition reduced to a boolean" in text:
        return "the IC simplified before solving; use equations like y(0)=1 or y'(0)=0"
    if "initial condition must be an equation" in text and expr:
        compact = re.sub(r"\s+", "", expr)
        if "d(y,x).subs" in compact or "d(f,x).subs" in compact:
            return "use y'(0)=... or d(y(x), x).subs(x, 0)=... for derivative initial conditions"
    if "data type not understood" in text:
        if expr and "matrix(" in expr.lower():
            return "matrix syntax: Matrix([[1,2],[3,4]])"
    if "blocked token" in text:
        return "remove blocked patterns like '__', ';', or newlines"
    if "integer power too large to evaluate exactly" in text:
        return (
            "power too large to expand exactly; simplify to cancel first "
            "(for example 10^N + 1 - 10^N), or use a smaller exponent"
        )
    if "factorial input too large to evaluate exactly" in text:
        return "factorial grows very fast; use a smaller n or a symbolic form"
    if "int_max_str_digits" in text:
        return "integer input is too large to materialize; simplify or use a symbolic form first"
    if "empty expression" in text:
        return "enter a math expression, or use :examples"
    for pattern, hint in FALLBACK_HINT_PATTERNS:
        if pattern.search(text):
            return hint
    return None
