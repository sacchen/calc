import calc.diagnostics as diagnostics


def test_should_print_wolfram_hint_policy():
    assert diagnostics.should_print_wolfram_hint(ValueError("cannot assign reserved name: f")) is False
    assert (
        diagnostics.should_print_wolfram_hint(
            ValueError("integer power too large to evaluate exactly (max exponent 1000000)")
        )
        is False
    )
    assert (
        diagnostics.should_print_wolfram_hint(
            ValueError("factorial input too large to evaluate exactly (max n 100000)")
        )
        is False
    )
    assert diagnostics.should_print_wolfram_hint(
        ValueError(
            "Exceeds the limit (4300 digits) for integer string conversion; "
            "use sys.set_int_max_str_digits() to increase the limit"
        )
    ) is False
    assert diagnostics.should_print_wolfram_hint(ValueError("different error")) is True


def test_parse_explanation_enabled_and_disabled():
    assert diagnostics.parse_explanation("sinx", relaxed=True, enabled=False) is None
    assert diagnostics.parse_explanation("sinx", relaxed=True, enabled=True) == "parsed as: sin(x)"
    assert "precedence: -a^b means -(a^b)" in diagnostics.parse_explanation(
        "-2^2",
        relaxed=True,
        enabled=True,
    )


def test_relaxed_rewrite_messages_deduplicates_and_strict_mode():
    assert diagnostics.relaxed_rewrite_messages("sinx + sinx", relaxed=True) == ["interpreted 'sinx' as 'sin(x)'"]
    assert diagnostics.relaxed_rewrite_messages("sinx", relaxed=False) == []


def test_eq_has_top_level_comma_edge_cases():
    assert diagnostics.eq_has_top_level_comma("x + y") is True
    assert diagnostics.eq_has_top_level_comma("Eq(d(y(x), x), y(x))") is True
    assert diagnostics.eq_has_top_level_comma("Eq(d(y(x), x) y(x))") is False


def test_hint_for_error_additional_branches():
    assert "derivative syntax" in diagnostics.hint_for_error("Unexpected EOF while parsing", expr="d(x")
    assert "check commas and brackets" in diagnostics.hint_for_error("invalid syntax", expr="foo(")
    assert "ambiguous trig shorthand" in diagnostics.hint_for_error("invalid syntax", expr="sin x^2")
    assert "try 'ff'" in diagnostics.hint_for_error(
        "cannot assign reserved name: f",
        session_locals={"ff": 1},
    )
    assert "derivative syntax" in diagnostics.hint_for_error("name 'a' is not defined", expr="d(a)")
    assert diagnostics.hint_for_error("data type not understood", expr="Matrix([1,2],[3,4])") == "matrix syntax: Matrix([[1,2],[3,4]])"
    assert "linalg syntax" in diagnostics.hint_for_error("unknown linalg subcommand")
    assert "gcd syntax" in diagnostics.hint_for_error(
        "gcd() takes 2 arguments or a sequence of arguments",
        expr="gcd(8)",
    )
    assert "lcm syntax" in diagnostics.hint_for_error(
        "lcm() takes 2 arguments or a sequence of arguments",
        expr="lcm(8)",
    )
    assert "isprime expects an integer" in diagnostics.hint_for_error(
        "x is not an integer",
        expr="isprime(x)",
    )
    assert "factorint expects an integer" in diagnostics.hint_for_error(
        "1/2 is not an integer",
        expr="factorint(1/2)",
    )
    assert "num syntax" in diagnostics.hint_for_error(
        "_num() missing 1 required positional argument: 'expr'",
        expr="num()",
    )
    assert "den syntax" in diagnostics.hint_for_error(
        "_den() missing 1 required positional argument: 'expr'",
        expr="den()",
    )
    assert "power too large to expand exactly" in diagnostics.hint_for_error(
        "integer power too large to evaluate exactly (max exponent 1000000)",
        expr="10^10000000000 + 1",
    )
    assert "factorial grows very fast" in diagnostics.hint_for_error(
        "factorial input too large to evaluate exactly (max n 100000)",
        expr="100001!",
    )
    assert "integer input is too large to materialize" in diagnostics.hint_for_error(
        "Exceeds the limit (4300 digits) for integer string conversion; "
        "use sys.set_int_max_str_digits() to increase the limit",
        expr="(100001)!",
    )


def test_hint_for_error_fallback_patterns_and_no_noise():
    assert diagnostics.hint_for_error(
        "('unterminated string literal (detected at line 1)', (1, 3))",
        expr="S('x')",
    ) == "check quote balance: close every ' or \" in the expression"
    assert diagnostics.hint_for_error(
        "EOF in multi-line statement",
        expr="(2+3",
    ) == "check missing closing ')' or unmatched quote"
    assert diagnostics.hint_for_error("unexpected character after line continuation character") == (
        "remove stray backslashes; enter plain math syntax"
    )
    assert diagnostics.hint_for_error("different error") is None
