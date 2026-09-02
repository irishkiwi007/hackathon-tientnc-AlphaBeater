"""Calculate factor expressions without using Python eval."""

import ast
import math
from collections.abc import Callable
from typing import Any

import pandas as pd

from alphabeater.dsl import ALLOWED_FIELDS, validate_expression


class FactorCalculationError(ValueError):
    pass


class FactorCalculator:
    def calculate(self, frame: pd.DataFrame, expression: str) -> pd.Series:
        validate_expression(expression)
        self._validate_frame(frame)
        ordered = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        tree = ast.parse(expression, mode="eval")
        result = self._visit(tree.body, ordered)
        if not isinstance(result, pd.Series):
            raise FactorCalculationError("factor expression must produce a series")
        result = pd.to_numeric(result, errors="coerce")
        result = result.where(result.map(lambda value: pd.isna(value) or math.isfinite(value)))
        if result.notna().sum() == 0:
            raise FactorCalculationError("factor expression produced no usable values")
        if result.dropna().nunique() < 2:
            raise FactorCalculationError("factor expression produced a constant value")
        result.name = expression
        return result

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        required = {"symbol", "timestamp", *ALLOWED_FIELDS}
        missing = required - set(frame.columns)
        if missing:
            raise FactorCalculationError(f"market data is missing columns: {sorted(missing)}")
        if frame.empty:
            raise FactorCalculationError("market data is empty")

    def _visit(self, node: ast.AST, frame: pd.DataFrame) -> pd.Series | float | int:
        if isinstance(node, ast.Name):
            return pd.to_numeric(frame[node.id], errors="coerce")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            raise FactorCalculationError("unsupported factor syntax")

        name = node.func.id
        args = [self._visit(argument, frame) for argument in node.args]
        binary: dict[str, Callable[[Any, Any], Any]] = {
            "add": lambda left, right: left + right,
            "sub": lambda left, right: left - right,
            "mul": lambda left, right: left * right,
            "div": lambda left, right: left / right,
        }
        if name in binary:
            self._require_arity(name, args, 2)
            return binary[name](args[0], args[1])
        if name == "neg":
            self._require_arity(name, args, 1)
            return -args[0]
        if name in {"delay", "returns", "ts_mean", "ts_std", "ts_min", "ts_max"}:
            self._require_arity(name, args, 2)
            series = self._require_series(name, args[0])
            window = self._require_window(name, args[1])
            grouped = series.groupby(frame["symbol"], sort=False)
            if name == "delay":
                return grouped.shift(window)
            if name == "returns":
                return grouped.pct_change(periods=window, fill_method=None)
            method = name.removeprefix("ts_")
            return grouped.transform(
                lambda values: getattr(values.rolling(window, min_periods=window), method)()
            )
        if name == "relative_volume":
            self._require_arity(name, args, 2)
            volume = self._require_series(name, args[0])
            window = self._require_window(name, args[1])
            average = volume.groupby(frame["symbol"], sort=False).transform(
                lambda values: values.rolling(window, min_periods=window).mean()
            )
            return volume / average
        if name in {"rank", "zscore"}:
            self._require_arity(name, args, 1)
            series = self._require_series(name, args[0])
            grouped = series.groupby(frame["timestamp"], sort=False)
            if name == "rank":
                return grouped.rank(pct=True)
            mean = grouped.transform("mean")
            std = grouped.transform("std")
            return (series - mean) / std
        raise FactorCalculationError(f"operator is not implemented: {name}")

    @staticmethod
    def _require_arity(name: str, args: list[Any], expected: int) -> None:
        if len(args) != expected:
            raise FactorCalculationError(f"{name} expects {expected} arguments")

    @staticmethod
    def _require_series(name: str, value: Any) -> pd.Series:
        if not isinstance(value, pd.Series):
            raise FactorCalculationError(f"{name} expects a data series")
        return value

    @staticmethod
    def _require_window(name: str, value: Any) -> int:
        if type(value) is not int or value < 1 or value > 252:
            raise FactorCalculationError(f"{name} window must be an integer from 1 to 252")
        return value
