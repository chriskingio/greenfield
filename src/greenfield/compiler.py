import ast
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module
from typing import Type
from types import ModuleType
import logging

from lark import Lark, Tree

from greenfield import __file__ as greenfield_pkg
from greenfield import resources
from greenfield.bundle import Bundle
from greenfield.resources import Resource
from greenfield.transformer import BundleTransformer

__log__ = logging.getLogger(__name__)

LIB = Path(greenfield_pkg).parent


def load_grammar() -> Lark:
    with open(LIB / 'grammar.lark', 'r') as f:
        return Lark(f, propagate_positions=True, parser='lalr')


def discover_resources():
    # TODO: discover optional paths as well?
    for importer, modname, ispkg in iter_modules(resources.__path__):
        if not ispkg:
            import_module(f'greenfield.resources.{modname}')


def greenfield_parse(source: str, filename: str) -> list[ast.stmt]:
    # Parse
    grammar = load_grammar()
    tree = grammar.parse(source)

    # AST pass
    transformer = BundleTransformer()
    result = transformer.transform(tree)
    __log__.debug(result)
    if isinstance(result, Tree):
        __log__.debug(result.children)
        # TODO: fix this typing a bit better rather than just ignoring it
        return result.children # type: ignore[return-value]
    __log__.debug(result)
    return result if isinstance(result, list) else [result]


def greenfield_compile_source(source: str, filename: str) -> ModuleType:
    # TODO: is this needed, or should this be called before
    # we ever get to a compilation step
    discover_resources()

    source_ast = greenfield_parse(source, filename)

    # Make a module
    module = ast.Module(body=source_ast, type_ignores=[])
    ast.fix_missing_locations(module)

    # bytecode
    code = compile(module, filename, 'exec')

    # create module
    module = ModuleType(Path(filename).stem)
    module.__file__ = filename

    namespace = {
        'Bundle': Bundle,
        'Resource': Resource,
    }
    exec(code, namespace)

    for name, obj in namespace.items():
        setattr(module, name, obj)

    return module


def greenfield_compile_file(filepath: str | Path) -> ModuleType:
    path = Path(filepath)
    source = path.read_text()
    return greenfield_compile_source(source, filename=str(path))
