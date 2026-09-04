"""Validation for AlphaBeater's deliberately small factor DSL."""

import ast

ALLOWED_FIELDS = frozenset({"open", "high", "low", "close", "volume", "vwap"})
ALLOWED_OPERATORS = frozenset(
    {
        "add",
        "sub",
        "mul",
        "div",
        "neg",
        "rank",
        "zscore",
        "delay",
        "returns",
        "ts_mean",
        "ts_std",
        "ts_min",
        "ts_max",
        "relative_volume",
        "abs",
        "sign",
        "demean",
        "ts_rank",
        "ts_corr",
        "decay_linear",
    }
)


#: Human-readable call signature for every registered operator.
#:
#: Prompts are built from this, so a model is told the exact arity instead of guessing.
#: `rank` and `zscore` are cross-sectional and take a series only — passing them a window
#: is the single most common mistake a model makes. Every entry must stay in step with
#: `ALLOWED_OPERATORS` and with the operator table in `factor_calculator.py`;
#: `test_dsl.py` enforces the first half of that.
OPERATOR_SIGNATURES: dict[str, str] = {
    "add": "add(a, b)",
    "sub": "sub(a, b)",
    "mul": "mul(a, b)",
    "div": "div(a, b)",
    "neg": "neg(a)",
    "rank": "rank(series)  # cross-sectional, NO window argument",
    "zscore": "zscore(series)  # cross-sectional, NO window argument",
    "delay": "delay(series, window)",
    "returns": "returns(series, window)",
    "ts_mean": "ts_mean(series, window)",
    "ts_std": "ts_std(series, window)",
    "ts_min": "ts_min(series, window)",
    "ts_max": "ts_max(series, window)",
    "relative_volume": "relative_volume(volume, window)",
    "abs": "abs(a)  # size of a move, ignoring direction",
    "sign": "sign(a)  # -1, 0 or 1",
    "demean": (
        "demean(series)  # cross-sectional, NO window argument; "
        "this symbol minus the universe average that day - use it for relative strength"
    ),
    "ts_rank": "ts_rank(series, window)  # where today sits within its own recent history, 0 to 1",
    "ts_corr": "ts_corr(series_a, series_b, window)  # rolling correlation of two series",
    "decay_linear": "decay_linear(series, window)  # weighted average, recent days weighted more",
}


class DSLValidationError(ValueError):
    """Raised when an expression is outside the registered factor language."""


def validate_expression(expression: str) -> None:
    """Validate syntax and names without evaluating user- or model-authored text."""

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise DSLValidationError("invalid factor expression syntax") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_OPERATORS:
                raise DSLValidationError("factor expression uses an unknown operator")
            if node.keywords:
                raise DSLValidationError("keyword arguments are not allowed")
        elif isinstance(node, ast.Name):
            if node.id not in ALLOWED_FIELDS and node.id not in ALLOWED_OPERATORS:
                raise DSLValidationError(f"unknown field or operator: {node.id}")
        elif isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise DSLValidationError("only numeric constants are allowed")
        elif not isinstance(
            node,
            (ast.Expression, ast.Load),
        ):
            raise DSLValidationError(f"syntax node is not allowed: {type(node).__name__}")


def referenced_fields(expression: str) -> set[str]:
    validate_expression(expression)
    tree = ast.parse(expression, mode="eval")
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id in ALLOWED_FIELDS
    }
