import ast
import typing
from exc import UnknownTypeError

def copy_assignee(n, ctx):
    if isinstance(n, ast.Name):
        ret = ast.Name(id=n.id, ctx=ctx)
    elif isinstance(n, ast.Attribute):
        ret = ast.Attribute(value=n.value, attr=n.attr, ctx=ctx)
    elif isinstance(n, ast.Subscript):
        ret = ast.Subscript(value=n.value, slice=n.slice, ctx=ctx)
    elif isinstance(n, ast.List):
        elts = [copy_assignee(e, ctx) for e in n.elts]
        ret = ast.List(elts=elts, ctx=ctx)
    elif isinstance(n, ast.Tuple):
        elts = [copy_assignee(e, ctx) for e in n.elts]
        ret = ast.Tuple(elts=elts, ctx=ctx)
    elif isinstance(n, ast.Starred):
        ret = ast.Starred(value=copy_assignee(n.value, ctx), ctx=ctx)
    else: return n
    ast.copy_location(ret, n)
    return ret

def iter_type(ty):
    if isinstance(ty, typing.List):
        return ty.type
    else: return typing.Dyn

