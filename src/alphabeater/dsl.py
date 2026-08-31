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
    }
)


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
