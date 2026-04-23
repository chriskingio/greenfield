from typing import Self, Optional
from abc import abstractmethod
from weakref import ref

from greenfield.resources import Resource
from greenfield.state import Ok, Drift, Error


class Bundle:
    def __init__(self):
        self.resources: list[Resource] = []
        self.locals: dict = {}
        self.__init_bundle__()

    def __init_bundle__(self):
        ...

    def register_resource(self, resource: Resource, current_locals: Optional[dict] = None) -> Resource:
        resource.bundle = ref(self)

        if current_locals is not None:
            if 'self' in current_locals:
                current_locals.pop('self')
            self.locals.update(current_locals)

        self.resources.append(resource)
        return resource

    def apply(self):
        for resource in self.resources:
            result = resource.check()
            match result:
                case Ok():
                    print(f'{resource.name} already in desired state')
                    pass
                case Drift(diffs=diffs):
                    print('Drift detected:')
                    for diff in diffs:
                        print(diff)
                    resource.apply()
                case Error(message=m, exception=e):
                    print(f'Error: {m}')
                    print(f'Exception: {e!r}')
                case _:
                    print(f'Unmatched arm: {result}')
