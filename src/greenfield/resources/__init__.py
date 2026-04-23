from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Type, TYPE_CHECKING
from weakref import ReferenceType

from greenfield import state

if TYPE_CHECKING:
    from greenfield.bundle import Bundle


class Resource[ConfigT](ABC):
    _registry: dict[str, Type[Resource[Any]]] = {}

    def __init__(self, name: str, /, **kwargs):
        self.name = name
        self.config: ConfigT = kwargs # type: ignore[assignment]
        self.bundle: Optional[ReferenceType[Bundle]] = None

    def __init_subclass__(cls, *args, **kwargs) -> None:
        super().__init_subclass__(*args, **kwargs)
        Resource._registry[cls.__name__] = cls

    @abstractmethod
    def check(self) -> state.CheckResult:
        return state.Ok()

    @abstractmethod
    def apply(self): ...

    # TODO: consider letting it accept a string name to look up or a Resource inherited class
    # in that case, just look for foo.__class__.__name__ I guess?
    @classmethod
    def get(cls, name: str) -> Type[Resource]:
        return cls._registry[name]

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}:{self.name!r}, {self.config!r}>'
