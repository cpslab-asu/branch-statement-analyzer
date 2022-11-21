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
    _func: Callable[_P, tuple[dict[str, float], _T]]
    _func_src: ast.FunctionDef

    def __call__(self, *args: _P.args, **kwds: _P.kwargs) -> tuple[dict[str, float], _T]:
        return self._func(*args, **kwds)

    @property
    def ast(self) -> ast.FunctionDef:
        return self._func_src

    @property
    def src(self) -> str:
        return ast.unparse(self._func_src)


def instrument_function(func: Callable[_P, _T]) -> InstrumentedFunction[_P, _T]:
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
    if isinstance(expr, ast.Name):
        return expr.id

    if isinstance(expr, ast.Attribute):
        return variable_name(expr.value) + "." + expr.attr

    raise TypeError()


def _dict_assign_stmt(dict_name: str, key: str, value: ast.expr) -> ast.stmt:
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
    return ast.Subscript(
        value=ast.Name(id=dict_name, ctx=ast.Load()),
        slice=ast.Constant(value=key),
        ctx=ast.Load(),
    )


@singledispatch
def _instrument_expr(expr: ast.expr, dict_name: str) -> tuple[Optional[ast.stmt], ast.expr]:
    return (None, expr)


@_instrument_expr.register
def _(expr: ast.Name, dict_name: str) -> tuple[ast.stmt, ast.expr]:
    key = variable_name(expr)
    return (_dict_assign_stmt(dict_name, key, expr), _dict_load_expr(dict_name, key))


@_instrument_expr.register
def _(expr: ast.Attribute, dict_name: str) -> tuple[ast.stmt, ast.expr]:
    key = variable_name(expr)
    return (_dict_assign_stmt(dict_name, key, expr), _dict_load_expr(dict_name, key))


@singledispatch
def _instrument_condition(expr: ast.expr, dict_name: str) -> tuple[list[ast.stmt], ast.expr]:
    return ([], expr)


@_instrument_condition.register
def _(expr: ast.Compare, dict_name: str) -> tuple[list[ast.stmt], ast.expr]:
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
    return ([], stmt)


@_instrument_stmt.register
def _(stmt: ast.If, dict_name: str) -> tuple[list[ast.stmt], ast.stmt]:
    assignments, new_test = _instrument_condition(stmt.test, dict_name)
    new_stmt = ast.If(
        new_test, _instrument_block(dict_name, stmt.body), _instrument_block(dict_name, stmt.orelse)
    )

    return (assignments, new_stmt)


@_instrument_stmt.register
def _(stmt: ast.Return, dict_name: str) -> tuple[list[ast.stmt], ast.stmt]:
    new_return = ast.Return(
        value=ast.Tuple(elts=[ast.Name(id=dict_name, ctx=ast.Load()), stmt.value], ctx=ast.Load()),
    )

    return ([], new_return)


def _instrument_block(dict_name: str, block: list[ast.stmt]) -> list[ast.stmt]:
    instr_block = []

    for stmt in block:
        assignments, stmt_ = _instrument_stmt(stmt, dict_name)
        instr_block.extend(assignments)
        instr_block.append(stmt_)

    return instr_block
