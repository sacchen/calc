import pytest
from hypothesis import given
from hypothesis import strategies as st

import calc.cli as cli
from calc.core import MAX_EXPRESSION_CHARS, evaluate


@pytest.mark.unit
@given(st.integers(min_value=-10_000, max_value=10_000), st.integers(min_value=-10_000, max_value=10_000))
def test_property_integer_addition_matches_python(a: int, b: int):
    expr = f"{a}+{b}"
    assert str(evaluate(expr)) == str(a + b)


@pytest.mark.unit
@given(st.integers(min_value=-50, max_value=50))
def test_property_derivative_inference_matches_explicit(coef: int):
    inferred = str(evaluate(f"d({coef}*x^2 + x)"))
    explicit = str(evaluate(f"d({coef}*x^2 + x, x)"))
    assert inferred == explicit


@pytest.mark.unit
@given(
    head=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=0, max_size=40),
    blocked=st.sampled_from(["__", ";", "\n", "\r"]),
    tail=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=0, max_size=40),
)
def test_property_blocked_tokens_are_rejected(head: str, blocked: str, tail: str):
    with pytest.raises(ValueError, match="blocked token|empty expression"):
        evaluate(f"{head}{blocked}{tail}")


@pytest.mark.unit
@given(
    suffix=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=100)
)
def test_property_expressions_above_max_length_are_rejected(suffix: str):
    expr = "x" * (MAX_EXPRESSION_CHARS + len(suffix))
    with pytest.raises(ValueError, match="expression too long"):
        evaluate(expr)


@pytest.mark.unit
@given(
    lines=st.lists(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :-_=/.'\"\\",
            min_size=0,
            max_size=48,
        ),
        min_size=1,
        max_size=40,
    )
)
def test_property_repl_parser_survives_random_lines(lines: list[str]):
    original = cli._print_update_status
    cli._print_update_status = lambda: None
    tutorial_state = {"active": False, "index": 0}
    expected_value_errors = (
        "invalid REPL option input",
        "missing value for --format",
        "unknown format mode",
        "missing value for --color",
        "unknown color mode",
        "unknown option",
    )
    try:
        for raw in lines:
            expr = raw.strip()
            if not expr:
                continue
            try:
                if cli._tutorial_command(expr, tutorial_state):
                    continue
                if cli._handle_repl_command(expr, color_mode="never"):
                    continue
                cli._try_parse_repl_inline_options(expr)
            except EOFError:
                continue
            except SystemExit:
                continue
            except ValueError as exc:
                assert any(marker in str(exc) for marker in expected_value_errors)
    finally:
        cli._print_update_status = original
