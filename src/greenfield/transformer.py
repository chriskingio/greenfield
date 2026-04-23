import ast
import logging
from typing import Any

from lark import Transformer, v_args, Tree
from lark.tree import Meta


__all__ = ['BundleTransformer', 'GreenfieldTransformError']
__log__ = logging.getLogger(__name__)


class BundleTransformer(Transformer):
    @v_args(inline=True, meta=True)
    def bundle(self, meta: Meta, name, *args):
        # args is either (*statements) or (param_list, *statements)
        if args and isinstance(args[0], list) or args[0] is None:
            param_list, *statements = args
        else:
            param_list, statements = None, list(args)
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:bundle {name=} (params:{[x[0] for x in param_list or []]}) statements:{len(statements)}>')

        kwonlyargs = []
        kw_defaults = []
        if param_list:
            for arg, default in param_list:
                kwonlyargs.append(ast.arg(arg=arg))
                kw_defaults.append(default)

        for idx, stmt in enumerate(statements):
            if stmt is None:
                raise GreenfieldTransformError(
                    f'Statement {idx} is None in bundle "{name}" at line {meta.line}'
                )

        apply_method = ast.FunctionDef(
            name='__init_bundle__',
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg='self')],
                vararg=None,
                kwonlyargs=kwonlyargs,
                kw_defaults=kw_defaults,
                kwarg=None,
                defaults=[],
            ),
            body=list(statements) or [ast.Pass()],
            returns=None,
        )

        return ast.ClassDef(
            name=name,
            bases=[ast.Name(id='Bundle', ctx=ast.Load())],
            # TODO:
            body=[apply_method],
        )

    @v_args(inline=True, meta=True)
    def role(self, meta, name, *statements):
        for idx, stmt in enumerate(statements):
            if stmt is None:
                raise GreenfieldTransformError(
                    f'Statement {idx} is None in role "{name}" at line {meta.line}'
                )

        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:role {name=} statements:{len(statements)}>')
        # Until I figure out how a role technically differs, this is a Bundle-inherited class for now
        apply_method = ast.FunctionDef(
            name='__init_bundle__',
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg='self')],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=list(statements) or [ast.Pass()],
            returns=None,
        )

        return ast.ClassDef(
            name=name,
            bases=[ast.Name(id='Bundle', ctx=ast.Load())],
            # TODO:
            body=[apply_method],
        )

    def param_list(self, params):
        return list(params)

    @v_args(inline=True)
    def param(self, name, default):
        return (str(name), default)

    @v_args(inline=True, meta=True)
    def assignment(self, meta, name, value):
        if isinstance(value, str):
            value = ast.Name(id=value, ctx=ast.Load())
        return ast.Assign(
            targets=[ast.Name(id=name, ctx=ast.Store())],
            value=value
        )

    @v_args(inline=True)
    def for_loop(self, name, iterable, *body):
        if isinstance(iterable, str):
            iterable = ast.Name(id=iterable, ctx=ast.Load())

        return ast.For(
            target=ast.Name(id=name, ctx=ast.Store()),
            iter=iterable,
            body=list(body),
            orelse=[],
        )

    @v_args(inline=True, meta=True)
    def if_statement(self, meta: Meta, expression, *statements):
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:if_statement test={expression!r} statements:{len(statements)}>')
        if isinstance(expression, str):
            expression = ast.Name(id=expression, ctx=ast.Load())

        return ast.If(
            test=expression,
            body=list(statements),
            orelse=[],
        )

    @v_args(inline=True, meta=True)
    def resource(self, meta: Meta, name, value, props):
        # This turns the following greenfield
        # File '/path/to/file' {
        #   owner: 'king'
        #   template: 'foo.md.j2'
        # }
        # into
        # self.register_resource(Resource.get('File')('/path/to/file', **{'owner': 'king', 'template': 'foo.md.j2'}), locals())
        if isinstance(value, str):
            value = ast.Constant(value=value)
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:resource type={name} name={value}>')
        return ast.Expr(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='self', ctx=ast.Load()),
                    attr='register_resource',
                    ctx=ast.Load()
                ),
                args=[
                    # First arg: Resource.get(name)(value, **props)
                    ast.Call(
                        func=ast.Call(  # Resource.get(name)
                            func=ast.Attribute(
                                value=ast.Name(id='Resource', ctx=ast.Load()),
                                attr='get',
                                ctx=ast.Load()
                            ),
                            args=[ast.Constant(value=name)],
                            keywords=[],
                        ),
                        args=[value],  # value
                        keywords=[ast.keyword(value=props)],  # props
                    ),
                    # Second arg: locals()
                    ast.Call(
                        func=ast.Name(id='locals', ctx=ast.Load()),
                        args=[],
                        keywords=[]
                    )
                ],
                keywords=[]
            )
        )

    @v_args(inline=True)
    def dict(self, *items):
        keys = []
        values = []
        # You can technically do `foo = {}`; this makes items=(None,) so filter out None
        for k, v in filter(None, items):
            keys.append(k if isinstance(k, ast.AST) else ast.Constant(value=k))
            if isinstance(v, str):
                v = ast.Name(id=v, ctx=ast.Load())
            values.append(v)
        return ast.Dict(
            keys=keys,
            values=values,
        )

    def string(self, s):
        content = s[0].value[1:-1]
        return ast.Constant(value=content)

    @v_args(inline=True)
    def array(self, *items: ast.expr):
        return ast.List(
            elts=list(items),
            ctx=ast.Load(),
        )

    @v_args(meta=True, inline=True)
    def mul(self, meta: Meta, left, right):
        if isinstance(left, str):
            left = ast.Name(id=left, ctx=ast.Load())
        if isinstance(right, str):
            right = ast.Name(id=right, ctx=ast.Load())
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:mul {left} * {right}>')

        return ast.BinOp(
            left=left,
            op=ast.Mult(),
            right=right,
        )

    @v_args(meta=True, inline=True)
    def div(self, meta: Meta, left, right):
        if isinstance(left, str):
            left = ast.Name(id=left, ctx=ast.Load())
        if isinstance(right, str):
            right = ast.Name(id=right, ctx=ast.Load())
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:div {left} / {right}>')

        return ast.BinOp(
            left=left,
            op=ast.Div(),
            right=right,
        )

    @v_args(meta=True, inline=True)
    def add(self, meta: Meta, left, right):
        if isinstance(left, str):
            left = ast.Name(id=left, ctx=ast.Load())
        if isinstance(right, str):
            right = ast.Name(id=right, ctx=ast.Load())
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:add {left} + {right}>')

        return ast.BinOp(
            left=left,
            op=ast.Add(),
            right=right,
        )

    @v_args(meta=True, inline=True)
    def sub(self, meta: Meta, left, right):
        if isinstance(left, str):
            left = ast.Name(id=left, ctx=ast.Load())
        if isinstance(right, str):
            right = ast.Name(id=right, ctx=ast.Load())
        __log__.debug(f'<[{meta.line}:{meta.column}]BundleTransformer:sub {left} - {right}>')

        return ast.BinOp(
            left=left,
            op=ast.Sub(),
            right=right,
        )

    @v_args(inline=True)
    def kvpair(self, name, value):
        if isinstance(name, str):
            name = ast.Constant(value=name)
        return (name, value)

    @v_args(inline=True)
    def fstring(self, str_spec) -> ast.expr:
        # dirty hack to just pass off the string to ast directly
        module = ast.parse("f{}".format(str_spec))
        return module.body[0].value # type: ignore[union-attr]

    # Basic types
    true = lambda self, _ : ast.Constant(value=True)
    false = lambda self, _ : ast.Constant(value=False)
    null = lambda self, _ : ast.Constant(value=None)
    # TODO: better error handling
    NUMBER = lambda self, n: ast.Constant(value=int(n))
    NAME = str


class GreenfieldTransformError(Exception): ...
