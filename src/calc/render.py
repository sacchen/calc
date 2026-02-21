from __future__ import annotations

from json import dumps

from sympy import latex as to_latex


def format_result(value, format_mode: str) -> str:
    if format_mode == "plain":
        return str(value)
    if format_mode == "pretty":
        from sympy import pretty as to_pretty

        return to_pretty(value)
    rendered = to_latex(value)
    if format_mode == "latex-inline":
        return f"${rendered}$"
    if format_mode == "latex-block":
        return f"$$\n{rendered}\n$$"
    return rendered


def format_json_result(
    expr: str,
    relaxed: bool,
    value,
    *,
    normalize_expression_fn,
) -> str:
    normalized = normalize_expression_fn(expr, relaxed=relaxed)
    payload = {"input": expr, "parsed": normalized, "result": str(value)}
    return dumps(payload, separators=(",", ":"))


def render_value(
    value,
    *,
    format_mode: str,
    expr: str,
    relaxed: bool,
    normalize_expression_fn,
    parsed_expr: str | None = None,
) -> str:
    if format_mode == "json":
        if parsed_expr is None:
            return format_json_result(
                expr,
                relaxed,
                value,
                normalize_expression_fn=normalize_expression_fn,
            )
        payload = {"input": expr, "parsed": parsed_expr, "result": str(value)}
        return dumps(payload, separators=(",", ":"))
    return format_result(value, format_mode)
