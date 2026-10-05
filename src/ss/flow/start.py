from types import TracebackType
from typing import Self, override

from PySide6.QtCore import QMutex, QObject, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioSink, QAudioSource
from shiboken6 import isValid

from ss.common import Config
from ss.external import Split
from ss.external.volume import Volume


class Start(QObject):
    finished = Signal(object, object, object)
    _mutex = QMutex()

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
            self._mutex.try_lock()
            self._mutex.unlock()
            has_split: bool = hasattr(self, "_split") and isValid(self._split)
            has_volume: bool = hasattr(self, "_volume") and isValid(self._volume)
            if has_split:
                self._split.finished.disconnect(self.__exit__)
            if has_volume:
                self._volume.finished.disconnect(self.__exit__)
            try:
                if has_split:
                    try:
                        self._split.__exit__(exc_type, exc, tb)
                    finally:
                        self._split.deleteLater()
            finally:
                if has_volume:
                    try:
                        self._volume.__exit__(exc_type, exc, tb)
                    finally:
                        self._volume.deleteLater()
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
                self.__exit__(exc_type, exc, tb)
                return
            if not self._mutex.try_lock():
                return
            left_device: QAudioDevice | None = self._config.left_device
            right_device: QAudioDevice | None = self._config.right_device
            source_device: QAudioDevice | None = self._config.source_device
            volume: QAudioDevice | None = self._config.volume_device
            if left_device is None:
                raise RuntimeError("未选择左声道输出")
            if right_device is None:
                raise RuntimeError("未选择右声道输出")
            if source_device is None:
                raise RuntimeError("未选择音频输入源")
            if left_device == right_device:
                raise RuntimeError("左右声道输出不能为同一个设备")
            left = QAudioSink(left_device)
            right = QAudioSink(right_device)
            source = QAudioSource(source_device)
            self._split = Split(
                left,
                right,
                source,
                left_latency=self._config.left_latency,
                right_latency=self._config.right_latency,
                parent=self,
            )
            self._split.finished.connect(self.__exit__)
            self._split(None, None, None)
            if volume is not None:
                self._volume = Volume(left, right, volume, parent=self)
                self._volume.finished.connect(self.__exit__)
                self._volume(None, None, None)
        except BaseException as e:
            self.__exit__(type(e), e, e.__traceback__)
            raise
