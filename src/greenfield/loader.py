from pathlib import Path
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec
from sys import meta_path, path as sys_path
from types import ModuleType
from typing import Optional

from greenfield.compiler import greenfield_compile_file

class GreenfieldFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None) -> Optional[ModuleSpec]:
        parts = fullname.split('.')
        module_name = parts[-1]

        search_paths = path if path else sys_path
        for search_path in search_paths:
            gf_path = Path(search_path) / f'{module_name}.gf'
            if gf_path.exists():
                return  ModuleSpec(
                    name=fullname,
                    loader=GreenfieldLoader(gf_path),
                    origin=str(gf_path),
                )
        return None


class GreenfieldLoader(Loader):
    def __init__(self, filepath):
        self.filepath = filepath

    def create_module(self, spec):
        return None

    def exec_module(self, module: ModuleType) -> None:
        compiled_module = greenfield_compile_file(self.filepath)

        module.__dict__.update(compiled_module.__dict__)
        module.__file__ = str(self.filepath)


def install():
    if not any(isinstance(f, GreenfieldFinder) for f in sys.meta_path):
        meta_path.insert(0, GreenfieldFinder())
