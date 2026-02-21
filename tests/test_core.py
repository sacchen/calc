import pytest

from calc.core import evaluate, normalize_expression, reserved_name_suggestion


def test_exact_arithmetic():
    assert str(evaluate("1/3 + 1/6")) == "1/2"


def test_derivative():
    assert str(evaluate("d(x^3 + 2*x, x)")) == "3*x**2 + 2"


def test_derivative_leibniz_shorthand():
    assert str(evaluate("d(sin(x))/dx")) == "cos(x)"


def test_derivative_leibniz_with_function():
    assert str(evaluate("df(t)/dt")) == "Derivative(f(t), t)"


def test_ode_shorthand_equation_normalizes():
    assert str(evaluate("dy/dx = y")) == "Eq(y(x), Derivative(y(x), x))"


def test_ode_prime_notation_equation_normalizes():
    assert str(evaluate("y' = y")) == "Eq(y(x), Derivative(y(x), x))"


def test_second_order_ode_prime_notation():
    assert str(evaluate("y'' + y = 0")) == "Eq(y(x) + Derivative(y(x), (x, 2)), 0)"


def test_latex_leibniz_ode_equation_normalizes():
    assert str(evaluate(r"\frac{dy}{dx} = y")) == "Eq(y(x), Derivative(y(x), x))"


def test_latex_higher_derivative_ode_equation_normalizes():
    assert str(evaluate(r"\frac{d^2y}{dx^2} + y = 0")) == "Eq(y(x) + Derivative(y(x), (x, 2)), 0)"


def test_markdown_wrapped_expression():
    assert str(evaluate("$d(x^2, x)$")) == "2*x"


@pytest.mark.parametrize(
    "expr",
    [
        "'d(x^2, x)'",
        '"d(x^2, x)"',
        "$$d(x^2, x)$$",
        r"\(d(x^2, x)\)",
        r"\[d(x^2, x)\]",
    ],
)
def test_additional_wrapped_expression_forms(expr: str):
    assert str(evaluate(expr)) == "2*x"


def test_latex_fraction_normalization():
    assert str(evaluate(r"\frac{1}{2}")) == "1/2"


def test_derivative_infers_single_symbol():
    assert str(evaluate("d(x^3 + 2*x)")) == "3*x**2 + 2"


def test_derivative_inference_ambiguous():
    with pytest.raises(ValueError, match="ambiguous variable"):
        evaluate("d(x*y)")


def test_derivative_inference_no_symbols():
    with pytest.raises(ValueError, match="no symbols found"):
        evaluate("d(42)")


def test_integral():
    assert str(evaluate("int(sin(x), x)")) == "-cos(x)"


def test_integral_infers_single_symbol():
    assert str(evaluate("int(sin(x))")) == "-cos(x)"


def test_integral_inference_ambiguous():
    with pytest.raises(ValueError, match="ambiguous variable"):
        evaluate("int(x + y)")


def test_integral_inference_no_symbols():
    with pytest.raises(ValueError, match="no symbols found"):
        evaluate("int(7)")


def test_solve():
    assert str(evaluate("solve(x^2 - 4, x)")) == "[-2, 2]"


def test_numeric_eval():
    assert str(evaluate("N(pi, 10)")) == "3.141592654"


def test_matrix_helpers():
    assert str(evaluate("det(Matrix([[1,2],[3,4]]))")) == "-2"
    assert str(evaluate("rank(Matrix([[1,2],[2,4]]))")) == "1"
    rref_out = str(evaluate("rref(Matrix([[1,2],[2,4]]))"))
    assert "[1, 2]" in rref_out
    assert "[0, 0]" in rref_out
    assert rref_out.endswith(", (0,))")
    assert str(evaluate("nullspace(Matrix([[1,2],[2,4]]))")) == "[Matrix([\n[-2],\n[ 1]])]"
    assert str(evaluate("msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))")) == "Matrix([[1/5], [3/5]])"
    assert str(evaluate("linsolve((Eq(2*x + y, 1), Eq(x + 3*y, 2)), (x, y))")) == "{(1/5, 3/5)}"


def test_assignment_and_ans_with_session_locals():
    session = {}
    assert str(evaluate("a = x^2 + 1", session_locals=session)) == "x**2 + 1"
    assert "a" in session
    assert str(evaluate("d(a)", session_locals=session)) == "2*x"
    assert str(evaluate("ans + 3", session_locals=session)) == "2*x + 3"


def test_assignment_rejects_reserved_name():
    with pytest.raises(ValueError, match="reserved name"):
        evaluate("sin = 2", session_locals={})


def test_reserved_name_suggestion_prefers_close_session_name():
    assert reserved_name_suggestion("f", {"ff": 1, "alpha": 2}) == "ff"
    assert reserved_name_suggestion("alpah", {"alpha": 2}) == "alpha"
    assert reserved_name_suggestion("f", {"alpha": 2}) is None


def test_no_simplify_mode():
    out = str(evaluate("sin(x)^2 + cos(x)^2", simplify_output=False))
    assert "sin(x)**2" in out
    assert "cos(x)**2" in out


def test_blocks_import_injection():
    with pytest.raises(ValueError, match="blocked token"):
        evaluate('__import__("os").system("echo bad")')


def test_blocks_empty_expression():
    with pytest.raises(ValueError, match="empty expression"):
        evaluate("   ")


def test_blocks_dunder_access():
    with pytest.raises(ValueError, match="blocked token"):
        evaluate("x.__class__")


def test_blocks_long_expression():
    expr = "1+" * 2000 + "1"
    with pytest.raises(ValueError, match="expression too long"):
        evaluate(expr)


def test_blocks_newline_and_semicolon():
    with pytest.raises(ValueError, match="blocked token"):
        evaluate("1+2\n3")
    with pytest.raises(ValueError, match="blocked token"):
        evaluate("1+2;3")


def test_normalizes_ln_and_unicode_minus():
    assert str(evaluate("ln(x)")) == "log(x)"
    assert str(evaluate("2−1")) == "1"


def test_normalizes_latex_commands():
    assert str(evaluate(r"\sin(x)^2 + \cos(x)^2", simplify_output=False)) == "sin(x)**2 + cos(x)**2"
    assert str(evaluate(r"\ln(x)")) == "log(x)"
    assert str(evaluate(r"\sqrt{x}")) == "sqrt(x)"


def test_function_exponentiation_parsing():
    assert str(evaluate("sin^2(x) + cos^2(x)", simplify_output=False)) == "sin(x)**2 + cos(x)**2"


def test_relaxed_parses_braces_ln_and_implicit_multiplication():
    expr = "(1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)"
    out = str(evaluate(expr, relaxed=True))
    assert "exp(-5*t)" in out
    assert "log(t)" in out


def test_relaxed_parses_second_long_expression():
    expr = "(854/2197)e^{8t}+(1343/2197)e^{-5t}+((9/26)t^2 -(9/169)t)e^{8t}"
    out = str(evaluate(expr, relaxed=True))
    assert "exp(" in out
    assert "exp(-5*t)" in out


def test_relaxed_interprets_sinx_shorthand():
    assert str(evaluate("sinx", relaxed=True)) == "sin(x)"


def test_strict_rejects_sinx_shorthand():
    with pytest.raises(NameError, match="sinx"):
        evaluate("sinx", relaxed=False)


def test_dsolve_with_y_of_x_notation():
    out = str(evaluate("dsolve(Eq(d(y(x), x), y(x)), y(x))", relaxed=True))
    assert "Eq(y(x), C1*exp(x))" in out


def test_ode_shorthand_for_f_of_t_equation_normalizes():
    normalized = normalize_expression("df/dt = f")
    assert normalized == "Eq(d(f(t), t), f(t))"
