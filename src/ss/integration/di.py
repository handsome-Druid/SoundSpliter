from dishka import (
    BaseScope,
    Container,
    Provider,
    Scope,
    make_container,
    provide,  # pyright: ignore[reportUnknownVariableType]
)
from dishka.dependency_source import CompositeDependencySource

from ss.common import Config
from ss.flow import Start


class DI:
    class _Provider(Provider):
        scope: BaseScope | None = Scope.APP
        _config: CompositeDependencySource = provide(
            source=Config.from_disk, provides=Config
        )
        _start: CompositeDependencySource = provide(source=Start)

    def __new__(cls) -> Container:
        return make_container(cls._Provider())
