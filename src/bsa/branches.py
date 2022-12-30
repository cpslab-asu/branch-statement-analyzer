from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from enum import Enum, auto
from functools import reduce
from typing import Any, Callable, Sequence, cast

from .instrumentation import variable_name
from .kripke import Kripke


class Comparison(Enum):
    LTE = auto()
    GTE = auto()

    def inverse(self) -> Comparison:
        if self is Comparison.LTE:
            return Comparison.GTE

        if self is Comparison.GTE:
            return Comparison.LTE

        raise ValueError(f"Unknown comparison type {self}")

    @staticmethod
    def from_op(op: ast.cmpop) -> Comparison:
        if isinstance(op, ast.LtE):
            return Comparison.LTE

        if isinstance(op, ast.GtE):
            return Comparison.GTE

        raise TypeError(f"Unsupported comparison operator {op}")


class InvalidConditionExpression(Exception):
    pass


@dataclass
class Condition:
    variable: str
    comparison: Comparison
    bound: str | float

    def inverse(self) -> Condition:
        return Condition(self.variable, self.comparison.inverse(), self.bound)
        
    def is_true(self, variables: dict[str, float]) -> bool:
        try:
            left = variables[self.variable]
        except KeyError:
            return False

        try:
            right = variables[self.bound] if isinstance(self.bound, str) else self.bound
        except KeyError:
            return False

        if self.comparison is Comparison.LTE:
            return left <= right
        elif self.comparison is Comparison.GTE:
            return left >= right
        else:
            raise ValueError(f"{self.comparison} is not a Comparison type")

    @property
    def variables(self) -> set[str]:
        if isinstance(self.bound, str):
            return set((self.variable, self.bound))
        else:
            return set((self.variable,))

    @classmethod
    def from_expr(cls, expr: ast.expr) -> Condition:
        if not isinstance(expr, ast.Compare):
            raise InvalidConditionExpression(f"Unsupported expression type {type(expr)}")

        left = expr.left
        comparison = Comparison.from_op(expr.ops[0])
        right = expr.comparators[0]
        variable_nodes = (ast.Name, ast.Attribute)

        if isinstance(left, variable_nodes) and isinstance(right, variable_nodes + (ast.Constant,)):
            if isinstance(right, variable_nodes):
                return cls(variable_name(left), comparison, variable_name(right))

            if isinstance(right, ast.Constant) and isinstance(right.value, (int, float)):
                return cls(variable_name(left), comparison, float(right.value))

            raise TypeError(f"Invalid bound type {type(right)}")

        if isinstance(left, ast.Constant) and isinstance(right, variable_nodes):
            if not isinstance(left.value, (int, float)):
                raise TypeError(f"Invalid bound type {type(right)}")

            return cls(variable_name(right), comparison.inverse(), float(left.value))

        raise TypeError("Invalid comparison expression")


@dataclass
class BranchTree:
    condition: Condition
    true_children: list[BranchTree]
    false_children: list[BranchTree]

    def as_kripke(self) -> list[Kripke[Condition]]:
        """Convert tree of conditions into a Kripke Structure."""

        if len(self.true_children) == 0:
            true_kripkes = [Kripke.singleton([self.condition])]
        else:
            true_kripkes = [
                kripke.add_labels([self.condition])
                for child in self.true_children
                for kripke in child.as_kripke()
            ]

        inv_cond = self.condition.inverse()

        if len(self.false_children) == 0:
            false_kripkes = [Kripke.singleton([inv_cond])]
        else:
            false_kripkes = [
                kripke.add_labels([inv_cond])
                for child in self.false_children
                for kripke in child.as_kripke()
            ]

        return [tk.join(fk) for (tk, fk) in zip(true_kripkes, false_kripkes)]

    @property
    def variables(self) -> set[str]:
        variables = self.condition.variables

        for child in self.true_children:
            variables = variables.union(child.variables)

        for child in self.false_children:
            variables = variables.union(child.variables)

        return variables

    @staticmethod
    def from_function(func: Callable[..., Any]) -> list[BranchTree]:
        mod_def = ast.parse(inspect.getsource(func))
        func_def = cast(ast.FunctionDef, mod_def.body[0])
        return _block_trees(func_def.body)


def _expr_trees(expr: ast.expr, tcs: list[BranchTree], fcs: list[BranchTree]) -> list[BranchTree]:
    if not isinstance(expr, ast.BoolOp):
        condition = Condition.from_expr(expr)
        tree = BranchTree(condition, tcs, fcs)
        return [tree]

    if isinstance(expr.op, ast.And):
        init = _expr_trees(expr.values[-1], tcs, fcs)
        trees = reduce(lambda ts, e: _expr_trees(e, ts, []), reversed(expr.values[:-1]), init)
        return list(trees)

    if isinstance(expr.op, ast.Or):
        return [tree for e in expr.values for tree in _expr_trees(e, tcs, fcs)]

    raise TypeError(f"Unsupported expression type {type(expr)}")


def _block_trees(block: Sequence[ast.stmt]) -> list[BranchTree]:
    block_trees = []
    conditions = [stmt for stmt in block if isinstance(stmt, ast.If)]

    for stmt in conditions:
        true_children = _block_trees(stmt.body)
        false_chilren = _block_trees(stmt.orelse)

        try:
            stmt_trees = _expr_trees(stmt.test, true_children, false_chilren)
        except InvalidConditionExpression:
            pass
        else:
            block_trees.extend(stmt_trees)

    return block_trees


__all__ = ["BranchTree", "Comparison", "Condition"]
