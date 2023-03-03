from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from functools import singledispatch
from typing import Callable, Generic, Optional, TypeVar, cast

from typing_extensions import ParamSpec

_P = ParamSpec("_P")
_T = TypeVar("_T")


@dataclass(frozen=True)
class InstrumentedFunction(Generic[_P, _T]):
    """Wrapper around an instrumented function."""

    _func: Callable[_P, tuple[dict[str, float], _T]]
    _func_src: ast.FunctionDef

    def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> tuple[dict[str, float], _T]:
        return self._func(*args, **kwds)

    @property
    def ast(self) -> ast.FunctionDef:
        """Return the instrumented funtion root AST node."""
        return self._func_src

    @property
    def src(self) -> str:
        """Return the instrumented function source"""
        return ast.unparse(self._func_src)


def instrument_function(func: Callable[_P, _T]) -> InstrumentedFunction[_P, _T]:
    """Decorator to instrument a function for Kripke analysis.

    Instrumentation of the function is accomplished by modifying the AST of the function to add
    assignment nodes before each conditional statement for each variable in the conditional
    expression. The conditional variables are stored in a dictionary that is initialized at the
    beginning of the function body. Each conditional expression variable read is replaced with a
    dictionary lookup instead. Finally, each return statement is transformed to return a tuple
    where the first element is the variable dictionary and the second element is the original
    return value.

    Args:
        func: The function to instrument

    Returns:
        A new function object with instrumentation code injected
    """

    func_tree = ast.parse(inspect.getsource(func))
    func_def = cast(ast.FunctionDef, func_tree.body[0])

    dict_name = "__vars"
    dict_statement = ast.parse(f"{dict_name} = dict()").body[0]
    func_def.body = [dict_statement] + _instrument_block(dict_name, func_def.body)
    func_def.name = f"{func_def.name}_instrumented"
    func_def.returns = ast.Subscript(
        value=ast.Name(id="tuple", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=[
                ast.Subscript(
                    value=ast.Name(id="dict", ctx=ast.Load()),
                    slice=ast.Tuple(
                        elts=[
                            ast.Name(id="str", ctx=ast.Load()),
                            ast.Name(id="float", ctx=ast.Load()),
                        ],
                        ctx=ast.Load(),
                    ),
                    ctx=ast.Load(),
                ),
                func_def.returns,
            ],
            ctx=ast.Load(),
        ),
        ctx=ast.Load(),
    )
    fixed_tree = ast.fix_missing_locations(func_tree)
    func_obj = compile(fixed_tree, filename="<instrumentation>", mode="exec")
    func_mod = inspect.getmodule(func)
    mod_defs = vars(func_mod)

    if func_mod is None:
        raise RuntimeError()

    exec(func_obj, mod_defs)  # pylint: disable=exec-used

    return InstrumentedFunction(mod_defs[func_def.name], func_def)


def variable_name(expr: ast.expr) -> str:
    """Determine the name of a variable represented as an AST node

    This function handles Name nodes which represent variable access by name, and Attribute nodes
    which represent accessing an attribute of a class. In the case of the attribute access, the
    class name is extracted and pre-prended to the recursive analysis of the attribute name.

    Examples:
    - foo.bar.baz = "foo.bar.baz"
    - spam = "spam"

    Args:
        expr: The AST expression node to analyze

    Returns:
        The name of the variable

    Raises:
        TypeError: If the AST node does not represent a variable
    """

    if isinstance(expr, ast.Name):
        return expr.id

    if isinstance(expr, ast.Attribute):
        return variable_name(expr.value) + "." + expr.attr

    raise TypeError()


def _dict_assign_stmt(dict_name: str, key: str, value: ast.expr) -> ast.stmt:
    """Create a dictionary value insertion statement.

    This function assumes that the dictionary and the value being inserted both already exist
    to be loaded by the python interpreter.

    Args:
        dict_name: The variable name of the dictionary to insert into
        key: The key to use for insertion
        value: The value to insert represented as an AST node

    Returns:
        An AST node representing the dictionary insertion statement
    """

    return ast.Assign(
        targets=[
            ast.Subscript(
                value=ast.Name(id=dict_name, ctx=ast.Load()),
                slice=ast.Constant(value=key),
                ctx=ast.Store(),
            )
        ],
        value=value,
    )


def _dict_load_expr(dict_name: str, key: str) -> ast.expr:
    """Create a dictionary value read expression.

    This function assumes that the dictionary to be read already exists to be load by the python
    interpreter and that the key exists to be read.

    Args:
        dict_name: The variable name of the dictionary to insert into
        key: The key to use for insertion
        value: The value to insert represented as an AST node

    Returns:
        An AST node representing the dictionary insertion statement
    """

    return ast.Subscript(
        value=ast.Name(id=dict_name, ctx=ast.Load()),
        slice=ast.Constant(value=key),
        ctx=ast.Load(),
    )


@singledispatch
def _instrument_expr(expr: ast.expr, dict_name: str) -> tuple[Optional[ast.stmt], ast.expr]:
    """Instrument an AST node that represents an expression.

    This function scans the expression node for a variable access. If one exists, a dictionary
    assignment statement is generated and the variable access in the expression is replaced with
    a dictionary access. If no variable access is found, the expression is unchanged and no
    assignment statement is generated.

    Args:
        expr: The expression to instrument
        dict_name: The name of the dictionary to use for storing and reading variable values

    Returns:
        An optional dictionary assignment statement and an instrumented expression
    """
    # pylint: disable=W0613

    return (None, expr)


@_instrument_expr.register
def _(expr: ast.Name, dict_name: str) -> tuple[ast.stmt, ast.expr]:
    """Single-dispatch variant specialized for AST Name nodes.

    For a Name node, this function extracts the variable name and generates a dictionary assignment
    and access pair to replace it.
    """

    key = variable_name(expr)
    return (_dict_assign_stmt(dict_name, key, expr), _dict_load_expr(dict_name, key))


@_instrument_expr.register
def _(expr: ast.Attribute, dict_name: str) -> tuple[ast.stmt, ast.expr]:
    """Single-dispatch variant specialized for AST Attribute nodes.

    For an Attribute node, this function extracts the variable name and generates a dictionary
    assignment and access pair to replace it.
    """

    key = variable_name(expr)
    return (_dict_assign_stmt(dict_name, key, expr), _dict_load_expr(dict_name, key))


@singledispatch
def _instrument_condition(expr: ast.expr, dict_name: str) -> tuple[list[ast.stmt], ast.expr]:
    """Instrument the guard expression of a conditional statment.

    This function instruments the expression by generating a dictionary assignment for each variable
    access in the expression and replacing each variable access in the expression with a dictionary
    access.

    If the expression is cannot be instrumented, then it is returned unchanged with an empty list of
    assignment statements.

    Args:
        expr: The guard expression to instrument
        dict_name: The name of the dictionary to use in the variable assignment statements

    Returns:
        A tuple containing the set of dictionary assignment statements for each variable in the
        expression and an instrumented expression with variable accesses replaced with dictionary
        accesses.
    """
    # pylint: disable=W0613

    return ([], expr)


@_instrument_condition.register
def _(expr: ast.Compare, dict_name: str) -> tuple[list[ast.stmt], ast.expr]:
    """Single-dispatch variant specialized for AST Compare nodes.

    An AST Compare node contains a left node and a list of right nodes. We instrument the left node
    and all right nodes while leaving the comparison operations unchanged.
    """

    assignments = []
    assignment, new_left = _instrument_expr(expr.left, dict_name)

    if assignment is not None:
        assignments.append(assignment)

    cmp_exprs = []

    for cmp_expr in expr.comparators:
        assignment, new_cmp_expr = _instrument_expr(cmp_expr, dict_name)

        if assignment is not None:
            assignments.append(assignment)

        cmp_exprs.append(new_cmp_expr)

    new_expr = ast.Compare(new_left, expr.ops, cmp_exprs)
    return (assignments, new_expr)


@_instrument_condition.register
def _(expr: ast.BoolOp, dict_name: str) -> tuple[list[ast.stmt], ast.expr]:
    """Single-dispatch variant specialized for AST BoolOp nodes.

    An AST BoolOp node contains an operation and several operands. In this case, we instrument
    every operand while leaving the operator unchanged.
    """

    assignments = []
    values = []

    for value in expr.values:
        assignments_, value_ = _instrument_condition(value, dict_name)
        assignments.extend(assignments_)
        values.append(value_)

    new_expr = ast.BoolOp(expr.op, values)

    return (assignments, new_expr)


@singledispatch
def _instrument_stmt(stmt: ast.stmt, dict_name: str) -> tuple[list[ast.stmt], ast.stmt]:
    """Instrument an statement.

    If the statement is a conditional statement then it is instrumented by generating a dictionary
    assignment statement for each variable in the statement guard condition and replacing each
    variable access in the guard with a dictionary access. The true and false blocks are then
    recursively instrumented.

    If the statement is a return statement then it is instrumented by creating a tuple AST node
    with the variable dictionary as the first component and the original return value as the
    second component.

    If the statement is not an conditional statement or return statement, then it is returned
    unchanged with an empty list of assignment statements.

    Args:
        stmt: The statement to instrument
        dict_name: The name of the dictionary to use for assignment and access statements

    Returns:
        A tuple containing a list of dictionary assignment statements and the instrumented statement
    """
    # pylint: disable=W0613

    return ([], stmt)


@_instrument_stmt.register
def _(stmt: ast.If, dict_name: str) -> tuple[list[ast.stmt], ast.stmt]:
    """Single-dispatch variant specialized for AST If nodes.

    To instrument the If node the guard expression node is instrumented and then the true block and
    false block are instrumented and added to the updated If node.
    """

    assignments, new_test = _instrument_condition(stmt.test, dict_name)
    new_stmt = ast.If(
        new_test, _instrument_block(dict_name, stmt.body), _instrument_block(dict_name, stmt.orelse)
    )

    return (assignments, new_stmt)


@_instrument_stmt.register
def _(stmt: ast.Return, dict_name: str) -> tuple[list[ast.stmt], ast.stmt]:
    """Single-dispatch variant specialized for AST Return nodes.

    To instrument the Return node a new Return node is generated that returns a Tuple literal node
    which contains the variable dictionary and the original return value.
    """

    new_return = ast.Return(
        value=ast.Tuple(elts=[ast.Name(id=dict_name, ctx=ast.Load()), stmt.value], ctx=ast.Load()),
    )

    return ([], new_return)


def _instrument_block(dict_name: str, block: list[ast.stmt]) -> list[ast.stmt]:
    """Instrument a block of statements.

    For each statement in the block, instrument it and append any generated assignment statements
    in front of the updated statement. If no statements can be instrumented, then the block is
    returned unchanged.

    Args:
        dict_name: The name of the dictionary to use for assignment and access statements
        block: List of statements to instrument

    Returns:
        A new block containing the generated assignment statements and instrumented statements.
    """

    instr_block = []

    for stmt in block:
        assignments, stmt_ = _instrument_stmt(stmt, dict_name)
        instr_block.extend(assignments)
        instr_block.append(stmt_)

    return instr_block
