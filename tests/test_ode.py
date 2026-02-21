import pytest
from sympy import Eq, Function, Symbol

from calc.core import evaluate
from calc.ode import evaluate_ode_alias, infer_ode_dependent, split_top_level_commas


def test_split_top_level_commas_handles_nested_parens():
    assert split_top_level_commas("y' = y, y(0)=1") == ["y' = y", "y(0)=1"]
    assert split_top_level_commas("Eq(d(y(x), x), y(x)), Eq(y(0), 1)") == [
        "Eq(d(y(x), x), y(x))",
        "Eq(y(0), 1)",
    ]


def test_infer_ode_dependent_returns_none_without_applied_function():
    x = Symbol("x")
    assert infer_ode_dependent(Eq(x, 1)) is None


def test_evaluate_ode_alias_success_without_ics():
    value, parsed = evaluate_ode_alias(
        "ode y' = y",
        evaluate_fn=evaluate,
        relaxed=True,
        simplify_output=True,
        session_locals={},
    )
    assert str(value) == "Eq(y(x), C1*exp(x))"
    assert parsed.startswith("dsolve(Eq(")


def test_evaluate_ode_alias_success_with_ics():
    value, parsed = evaluate_ode_alias(
        "ode y' = y, y(0)=1",
        evaluate_fn=evaluate,
        relaxed=True,
        simplify_output=True,
        session_locals={},
    )
    assert str(value) == "Eq(y(x), exp(x))"
    assert "ics={y(0): 1}" in parsed


def test_evaluate_ode_alias_raises_on_empty_body():
    with pytest.raises(ValueError, match="ode expects an equation"):
        evaluate_ode_alias(
            "ode ",
            evaluate_fn=evaluate,
            relaxed=True,
            simplify_output=True,
            session_locals={},
        )


def test_evaluate_ode_alias_raises_on_empty_pieces():
    with pytest.raises(ValueError, match="ode expects an equation"):
        evaluate_ode_alias(
            "ode , ,",
            evaluate_fn=evaluate,
            relaxed=True,
            simplify_output=True,
            session_locals={},
        )


def test_evaluate_ode_alias_requires_equation_and_dependent_function():
    def fake_eval(expr: str, **kwargs):
        if expr == "x+1":
            return 3
        return Eq(Symbol("x"), 1)

    with pytest.raises(ValueError, match="ode expects an equation"):
        evaluate_ode_alias(
            "ode x+1",
            evaluate_fn=fake_eval,
            relaxed=True,
            simplify_output=True,
            session_locals={},
        )

    with pytest.raises(ValueError, match="could not infer dependent function"):
        evaluate_ode_alias(
            "ode Eq(x, 1)",
            evaluate_fn=fake_eval,
            relaxed=True,
            simplify_output=True,
            session_locals={},
        )


def test_evaluate_ode_alias_validates_initial_conditions_and_passes_flags():
    y = Function("y")
    x = Symbol("x")
    calls: list[tuple[str, bool, bool, dict]] = []

    def fake_eval(expr: str, **kwargs):
        calls.append((expr, kwargs["relaxed"], kwargs["simplify_output"], kwargs["session_locals"]))
        if expr == "y' = y":
            return Eq(y(x), y(x).diff(x))
        return 1

    with pytest.raises(ValueError, match="initial condition must be an equation"):
        evaluate_ode_alias(
            "ode y' = y, 1",
            evaluate_fn=fake_eval,
            relaxed=False,
            simplify_output=False,
            session_locals={"a": 1},
        )

    assert calls[0] == ("y' = y", False, False, {"a": 1})
    assert calls[1] == ("1", False, False, {"a": 1})
