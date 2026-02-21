from __future__ import annotations

from sympy import Eq, dsolve
from sympy.core.function import AppliedUndef


def split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def infer_ode_dependent(eq_value: Eq):
    candidates = sorted(eq_value.atoms(AppliedUndef), key=str)
    if not candidates:
        return None
    return candidates[0]


def evaluate_ode_alias(
    expr: str,
    *,
    evaluate_fn,
    relaxed: bool,
    simplify_output: bool,
    session_locals: dict | None = None,
):
    body = expr[4:].strip()
    if not body:
        raise ValueError("ode expects an equation, e.g. ode y' = y")

    pieces = split_top_level_commas(body)
    if not pieces:
        raise ValueError("ode expects an equation, e.g. ode y' = y")
    equation_text, ic_texts = pieces[0], pieces[1:]

    eq_value = evaluate_fn(
        equation_text,
        relaxed=relaxed,
        session_locals=session_locals,
        simplify_output=simplify_output,
    )
    if not isinstance(eq_value, Eq):
        raise ValueError("ode expects an equation, e.g. ode y' = y")

    dep = infer_ode_dependent(eq_value)
    if dep is None:
        raise ValueError("could not infer dependent function; use y(x)-style notation")

    ics: dict = {}
    for ic_text in ic_texts:
        ic_value = evaluate_fn(
            ic_text,
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(ic_value, Eq):
            raise ValueError(f"initial condition must be an equation: {ic_text}")
        ics[ic_value.lhs] = ic_value.rhs

    if ics:
        result = dsolve(eq_value, dep, ics=ics)
        ics_rendered = ", ".join(f"{lhs}: {rhs}" for lhs, rhs in ics.items())
        parsed_expr = f"dsolve({eq_value}, {dep}, ics={{{ics_rendered}}})"
    else:
        result = dsolve(eq_value, dep)
        parsed_expr = f"dsolve({eq_value}, {dep})"
    return result, parsed_expr
