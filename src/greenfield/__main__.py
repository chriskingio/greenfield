import ast
from argparse import ArgumentParser, Namespace as APNamespace
from pathlib import Path
from sys import exit
import logging

from greenfield import __version__
import greenfield.compiler as compiler
from greenfield.bundle import Bundle
import greenfield.state as state


class Arguments(APNamespace):
    action: str
    # Check
    dump_ast: bool = False
    show_python: bool = False
    # Apply
    noop: bool = False
    bundle: str
    # Common
    file: str
    version: bool = False
    verbose: bool = False


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='greenfield')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--verbose', action='store_true')

    action = parser.add_subparsers(dest='action')
    # check action
    check = action.add_parser('check')
    check.add_argument('--dump-ast', action='store_true')
    check.add_argument('--show-python', action='store_true')
    check.add_argument('file')
    # apply action
    apply = action.add_parser('apply')
    apply.add_argument('--noop', action='store_true')
    apply.add_argument('file')
    apply.add_argument('bundle')

    return parser


def main() -> int:
    parser = get_parser()
    args: Arguments = parser.parse_args() # type: ignore

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.version:
        print(f'greenfield version {__version__}')
        return 0

    match args.action:
        case 'apply':
            module = compiler.greenfield_compile_file(args.file)
            bundles = {
                name: obj for name, obj in vars(module).items()
                if isinstance(obj, type) and issubclass(obj, Bundle) and obj is not Bundle
            }

            if not bundles:
                print('No bundles found in file')
                return 1

            if args.bundle not in bundles:
                print(f'{args.bundle} not found, available bundles: {", ".join(bundles.keys())}')
                return 3

            b = bundles[args.bundle]()
            for resource in b.resources:
                match resource.check():
                    case state.Ok():
                        print(f'  {resource.name}: ok')
                    case state.Drift(diffs=diffs):
                        if args.noop:
                            print(f'  {resource.name}: would change')
                        else:
                            print(f'  {resource.name}: applying changes')
                            resource.apply()
                        for diff in diffs:
                            print(f'    {diff}')
                    case state.Error(message=m, exception=e):
                        print(f'  {resource.name}: error - {m}')
                        if args.verbose and e:
                            print(f'    {e!r}')
        case 'check':
            source = Path(args.file).read_text()
            source_ast = compiler.greenfield_parse(source, args.file)
            module = ast.Module(body=source_ast, type_ignores=[])
            ast.fix_missing_locations(module)
            if args.dump_ast:
                print(ast.dump(module, indent=2))
            if args.show_python:
                print(ast.unparse(module))
        case None:
            parser.print_help()
            return 1
        case _:
            parser.print_help()
            return 2

    return 0


if __name__ == '__main__':
    exit(main())
