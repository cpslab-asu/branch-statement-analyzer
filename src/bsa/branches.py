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
    """Representation of the comparison operators <=, >=

    This class is confined to the operators that include equality because they are the easiest to
    support as STL formulas.

    Attributes:
        LTE: less than or equal to operator
        GTE: greater than or equal to operator
    """

    LTE = auto()
    GTE = auto()

    def inverse(self) -> Comparison:
        """Invert the comparion.

        Returns:
            The inverse comparison operator
        """

        if self is Comparison.LTE:
            return Comparison.GTE

        if self is Comparison.GTE:
            return Comparison.LTE

        raise ValueError(f"Unknown comparison type {self}")

    @staticmethod
    def from_op(op: ast.cmpop) -> Comparison:
        """Create a comparison from an AST node.

        Args:
            op: The AST comparison operator node

        Returns:
            The comparison operator of the node

        Raises:
            TypeError: If op is not an AST comparison node
        """

        if isinstance(op, ast.LtE):
            return Comparison.LTE

        if isinstance(op, ast.GtE):
            return Comparison.GTE

        raise TypeError(f"Unsupported comparison operator {op}")


class InvalidConditionExpression(Exception):
    pass


@dataclass
class Condition:
    """Representation of the boolean expression of a conditional statement.

    This representation assumes that the condition is represented as an inequality, with a varaible
    on at least one side of the equation.

    Attributes:
        variable: The name of the variable on the left side of the comparison
        comparison: The comparison operator
        bound: The value or variable on the right side of the comparison

    """
    variable: str
    comparison: Comparison
    bound: str | float

    def inverse(self) -> Condition:
        """Invert the condition.

        This function returns a new Condition instance rather than modifying the existing one.

        Returns:
            A new Condition with the comparison inverted
        """
        return Condition(self.variable, self.comparison.inverse(), self.bound)
        
    def is_true(self, variables: dict[str, float]) -> bool:
        """Check if a condition is true given a set of variables.

        If a variable is not present in the map, then the condition is assumed to be false.

        Args:
            variables: Mapping from variable names to values

        Returns:
            True if the condition is true, False otherwise

        Raises:
            ValueError: If the value in the comparison attribute is not the Comparison type
        """

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
        """The set of variables depended on by the condition."""

        if isinstance(self.bound, str):
            return set((self.variable, self.bound))
        else:
            return set((self.variable,))

    @classmethod
    def from_expr(cls, expr: ast.expr) -> Condition:
        """Create a Condition from an AST expression node.

        This class method assumes that the comparison expression only has a single operand. This is
        not always the case in Python as the expression "10 <= x <= 20" is a valid comparison and
        is represented by having several operands in the expression AST node.

        Args:
            expr: The AST expression node

        Returns:
            A Condition instance representing the AST comparison expression

        Raises:
            InvalidConditionExpresssion: If the expr value is not an ast.Compare type
            TypeErrror: If the expression does not conform to the condition assumptions
        """

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
    """Representation of a tree of conditional blocks.

    A tree represents an independent conditional statement i.e. a single if-else block. This tree
    has two sets of children, one of the conditional statements found in the true block of the
    conditional statement, and one of the conditional statements found in the false block.

    Attributes:
        condition: The boolean guard of the conditional block
        true_children: Sub-trees found in the block associated with the condition being true
        false_children: Sub-trees found in the block associated with the condition being false
    """

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
        """The set of variables depended on by the tree, including its children."""

        variables = self.condition.variables

        for child in self.true_children:
            variables = variables.union(child.variables)

        for child in self.false_children:
            variables = variables.union(child.variables)

        return variables

    @staticmethod
    def from_function(func: Callable[..., Any]) -> list[BranchTree]:
        """Create a set of BranchTrees from an arbitrary python function.

        The set of BranchTrees that represent all of the independent conditional statements in the
        function body. In other words, the size of the output set should be the same as the number
        of independent if-else blocks in the function. In order to analyze this function, the
        python source of the function should be available.

        Args:
            func: The python function to analyze

        Returns:
            A set of BranchTrees representing all independent conditional statements in the function

        Raises:
            OsError: If the source code of the function is not available
        """

        mod_def = ast.parse(inspect.getsource(func))
        func_def = cast(ast.FunctionDef, mod_def.body[0])
        return _block_trees(func_def.body)


def _expr_trees(expr: ast.expr, tcs: list[BranchTree], fcs: list[BranchTree]) -> list[BranchTree]:
    """Create a set of BranchTrees from a conditional statement expression.

    This function generates a set of trees in order to handle the cases in which the conditional
    statement expression contains either a boolean conjunction or disjunction operator. In the
    case of the conjunction, we traverse the set of operands generating a new tree with the operand
    as the condition and the previous tree as a true child. In the case of disjunction, we traverse
    the set of operands and create a new tree for each operand with the same children for each.

    Args:
        expr: The conditional statement expression
        tcs: The set of BranchTrees generated from the true block body
        fcs: The set of BranchTrees generated from the false block body

    Returns:
        A set of BranchTrees created from the expression

    Raises:
        TypeError: If the condition expression node is not a supported type
    """

    if not isinstance(expr, ast.BoolOp):
        condition = Condition.from_expr(expr)
        tree = BranchTree(condition, tcs, fcs)
        return [tree]

    if isinstance(expr.op, ast.And):
        """In this case, we compose a single tree by iteratively stacking BranchTrees for each
        operand. We explore this approach in the following example.

        Given the following condition:

            if x <= 5 and y <= 10:
                do_true()
            else:
                do_false()

        We can see that this can be re-written as the following:

            if x <= 5:
                if y <= 10:
                    do_true()
                else:
                    do_false()
            else:
                do_false()

        The re-written condition can now be analyzed recursively to produce a BranchTree.
        """

        init = _expr_trees(expr.values[-1], tcs, fcs)
        trees = reduce(lambda ts, e: _expr_trees(e, ts, []), reversed(expr.values[:-1]), init)
        return list(trees)

    if isinstance(expr.op, ast.Or):
        """In this case, we create a set of trees by iterating over the set of operands and
        creating new trees with the same children. Consider the following example.

        Given the following condition:

            if x <= 5 or y <= 10:
                do_true()
            else:
                do_false()

        This can be re-written as the following:

            if x <= 5:
                do_true()
            else:
                do_false()

            if y <= 10:
                do_true()
            else:
                do_false()

        The re-written condition can now be analyzed into a set of independent BranchTrees.
        """

        return [tree for e in expr.values for tree in _expr_trees(e, tcs, fcs)]

    raise TypeError(f"Unsupported expression type {type(expr)}")


def _block_trees(block: Sequence[ast.stmt]) -> list[BranchTree]:
    """Create a set of trees from a block of python statements.

    Each BranchTree in the set represents an independent conditional statement in the block. The
    true and false blocks of each statement are recursively analyzed to find the child BranchTrees.

    Args:
        block: The set of python statements in the block

    Returns:
        A set of BranchTrees representing the independent conditional statements in the block
    """

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
