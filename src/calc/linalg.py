from __future__ import annotations

from sympy.matrices.matrixbase import MatrixBase


def consume_bracket_literal(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "[":
        raise ValueError("expected bracketed literal like [[...]]")
    depth = 0
    idx = start
    while idx < len(text):
        ch = text[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1], idx + 1
        idx += 1
    raise ValueError("unclosed bracket literal; expected closing ']'")


def parse_linalg_keyed_literals(text: str, required_keys: set[str]) -> dict[str, str]:
    idx = 0
    parsed: dict[str, str] = {}
    while idx < len(text):
        while idx < len(text) and text[idx] in {",", " "}:
            idx += 1
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        key_start = idx
        while idx < len(text) and text[idx].isalpha():
            idx += 1
        key = text[key_start:idx]
        if key not in required_keys:
            expected = ", ".join(sorted(required_keys))
            raise ValueError(f"unknown linalg parameter '{key}'; expected: {expected}")
        if key in parsed:
            raise ValueError(f"duplicate linalg parameter '{key}'")
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] != "=":
            raise ValueError(f"linalg parameter '{key}' must use '='")
        idx += 1
        while idx < len(text) and text[idx].isspace():
            idx += 1
        literal, idx = consume_bracket_literal(text, idx)
        parsed[key] = literal

    missing = sorted(required_keys - set(parsed))
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"missing linalg parameter(s): {missing_text}")
    return parsed


def evaluate_linalg_alias(
    expr: str,
    *,
    evaluate_fn,
    relaxed: bool,
    simplify_output: bool,
    session_locals: dict | None = None,
):
    body = expr[7:].strip()
    if not body:
        raise ValueError("linalg expects a subcommand: solve, rref, det, inv, rank, eig, nullspace")
    pieces = body.split(maxsplit=1)
    subcommand = pieces[0].lower()
    rest = pieces[1] if len(pieces) > 1 else ""

    if subcommand == "solve":
        params = parse_linalg_keyed_literals(rest, {"A", "b"})
        matrix_text = params["A"]
        rhs_text = params["b"]
        matrix_value = evaluate_fn(
            f"Matrix({matrix_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        rhs_value = evaluate_fn(
            f"Matrix({rhs_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(matrix_value, MatrixBase) or not isinstance(rhs_value, MatrixBase):
            raise ValueError("linalg solve expects matrix literals for A and b")
        if matrix_value.rows != matrix_value.cols:
            raise ValueError("linalg solve expects square A")
        if rhs_value.cols != 1:
            raise ValueError("linalg solve expects b as a column vector, e.g. b=[1,2]")
        if rhs_value.rows != matrix_value.rows:
            raise ValueError("linalg solve expects len(b) to match rows of A")
        result = matrix_value.LUsolve(rhs_value)
        parsed_expr = f"msolve(Matrix({matrix_text}), Matrix({rhs_text}))"
        return result, parsed_expr

    if subcommand == "rref":
        params = parse_linalg_keyed_literals(rest, {"A"})
        matrix_text = params["A"]
        matrix_value = evaluate_fn(
            f"Matrix({matrix_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(matrix_value, MatrixBase):
            raise ValueError("linalg rref expects a matrix literal for A")
        result = matrix_value.rref()
        parsed_expr = f"rref(Matrix({matrix_text}))"
        return result, parsed_expr

    if subcommand in ("det", "inv", "rank", "nullspace", "eig", "eigvals"):
        params = parse_linalg_keyed_literals(rest, {"A"})
        matrix_text = params["A"]
        matrix_value = evaluate_fn(
            f"Matrix({matrix_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(matrix_value, MatrixBase):
            raise ValueError(f"linalg {subcommand} expects a matrix literal for A")
        if subcommand == "det":
            result = matrix_value.det()
            parsed_expr = f"det(Matrix({matrix_text}))"
        elif subcommand == "inv":
            result = matrix_value.inv()
            parsed_expr = f"inv(Matrix({matrix_text}))"
        elif subcommand == "rank":
            result = matrix_value.rank()
            parsed_expr = f"rank(Matrix({matrix_text}))"
        elif subcommand == "nullspace":
            result = matrix_value.nullspace()
            parsed_expr = f"nullspace(Matrix({matrix_text}))"
        else:  # eig / eigvals
            result = matrix_value.eigenvals()
            parsed_expr = f"eigvals(Matrix({matrix_text}))"
        return result, parsed_expr

    raise ValueError("unknown linalg subcommand; use: solve, rref, det, inv, rank, nullspace, eig")
