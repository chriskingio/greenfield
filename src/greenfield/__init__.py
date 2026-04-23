from typing import Final
import importlib.util
from importlib.metadata import version

__all__ = ['__version__']


def is_editable_install() -> bool:
    """Determines if the package is in development or not."""
    try:
        spec = importlib.util.find_spec('greenfield')
        if spec and spec.origin:
            return 'site-packages' not in spec.origin
    except Exception:
        # Assume dev?
        return True
    # Assume dev
    return True


__version__: Final[str] = 'dev' if is_editable_install() else version('greenfield')
