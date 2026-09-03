import pytest

from alphabeater.dsl import DSLValidationError, validate_expression


@pytest.mark.parametrize(
    "expression",
    [
        "returns(close, 5)",
        "neg(ts_std(returns(close, 1), 20))",
        "div(sub(close, vwap), ts_std(close, 20))",
    ],
)
def test_valid_expressions(expression: str) -> None:
    validate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('whoami')",
        "close.__class__",
        "unknown(close, 5)",
        "returns(adjusted_close, 5)",
        "[close]",
    ],
)
def test_rejects_unregistered_syntax(expression: str) -> None:
    with pytest.raises(DSLValidationError):
        validate_expression(expression)
