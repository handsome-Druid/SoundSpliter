from sys import exc_info, exception
from types import TracebackType
from typing import Self, override

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioSink, QAudioSource
from shiboken6 import isValid

from ss.common import Config
from ss.external import Split


class Start(QObject):
    finished = Signal(object, object, object)

    @override
    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config: Config = config

    def __enter__(self) -> Self:
        return self

    @Slot(object, object, object)
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
        /,
    ) -> None:
        try:
            if hasattr(self, "_split") and isValid(self._split):
                self._split.finished.disconnect(self.__exit__)
                self._split.__exit__(exc_type, exc, tb)
                self._split.deleteLater()
        finally:
            self.finished.emit(exc_type, exc, tb)

    @Slot(object, object, object)
    def __call__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
        /,
    ) -> None:
        try:
            if exc_type is not None:
                return
            left: QAudioDevice | None = self._config.left_device
            right: QAudioDevice | None = self._config.right_device
            source: QAudioDevice | None = self._config.source_device
            if left is None:
                raise RuntimeError("未选择左声道输出")
            if right is None:
                raise RuntimeError("未选择右声道输出")
            if source is None:
                raise RuntimeError("未选择音频输入源")
            self._split = Split(
                left=QAudioSink(left),
                right=QAudioSink(right),
                source=QAudioSource(source),
                left_latency=self._config.left_latency,
                right_latency=self._config.right_latency,
                parent=self,
            )
            self._split.finished.connect(self.__exit__)
            self._split(None, None, None)
        finally:
            if exc_type is not None:
                self.__exit__(exc_type, exc, tb)
            elif exception() is not None:
                self.__exit__(*exc_info())
