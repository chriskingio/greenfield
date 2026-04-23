from difflib import unified_diff
from typing import Optional
from dataclasses import dataclass
from numbers import Real

type BasicDiffableType = str | bool | Real | None
type DiffableType = BasicDiffableType | list[BasicDiffableType] | dict[str,BasicDiffableType]


@dataclass(frozen=True)
class StateDiff[T: DiffableType]:
    field: str
    expected: T
    actual: T

    def _format_diff(self) -> str:
        match (self.expected, self.actual):
            # Simple matches
            case (bool(), bool() | (Real(), Real()) | (None, None) | (None, _) | (_, None)):
                return f'{self.actual!r} -> {self.expected!r}'
            # str - diff only if the strs are big
            case (str(), str()):
                if '\n' not in self.expected and '\n' not in self.actual and len(self.expected) < 60:
                    return f'{self.actual!r} -> {self.expected!r}'
                expected_lines = self.expected.splitlines(keepends=True)
                actual_lines = self.actual.splitlines(keepends=True)
                diff = unified_diff(
                    actual_lines,
                    expected_lines,
                    fromfile='actual',
                    tofile='expected',
                )
                return '\n' + ''.join(diff)
            # list = render as string, diff
            case (list(), list()):
                expected_lines = [f'{v!r}\n' for v in self.expected]
                actual_lines = [f'{v!r}\n' for v in self.actual]
                diff = unified_diff(
                    actual_lines,
                    expected_lines,
                    fromfile='actual',
                    tofile='expected',
                )
                return '\n' + ''.join(diff)
            # dict - sort and then render like list
            case (dict(), dict()):
                expected_lines = [f'{k}: {v!r}\n' for k, v in sorted(self.expected.items())]
                actual_lines = [f'{k}: {v!r}\n' for k, v in sorted(self.actual.items())]
                diff = unified_diff(
                    actual_lines,
                    expected_lines,
                    fromfile='actual',
                    tofile='expected',
                )
                return '\n' + ''.join(diff)
            # other basics or fallback
            case _:
                return f'{self.actual!r} -> {self.expected!r}'

    def __str__(self) -> str:
        return f'{self.field}: {self._format_diff()}'

@dataclass(frozen=True)
class CheckResult: ...


@dataclass(frozen=True)
class Ok(CheckResult):
    pass


@dataclass(frozen=True)
class Drift(CheckResult):
    diffs: list[StateDiff]


@dataclass(frozen=True)
class Error(CheckResult):
    message: str
    exception: Optional[Exception] = None
