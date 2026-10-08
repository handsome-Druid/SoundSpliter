from types import TracebackType
from typing import Self, override

from PySide6.QtCore import QMetaObject, QMutex, QObject, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioSink, QAudioSource
from shiboken6 import isValid

from ss.external import Config, Split, Volume


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
        is_running: bool = not self._mutex.try_lock()
        try:
            try:
                if hasattr(self, "_split") and isValid(self._split):
                    try:
                        if hasattr(self, "_split_conn"):
                            self._split.finished.disconnect(self._split_conn)
                    finally:
                        try:
                            self._split.__exit__(exc_type, exc, tb)
                        finally:
                            self._split.deleteLater()
            finally:
                if hasattr(self, "_volume") and isValid(self._volume):
                    try:
                        if hasattr(self, "_volume_conn"):
                            self._volume.finished.disconnect(self._volume_conn)
                    finally:
                        try:
                            self._volume.__exit__(exc_type, exc, tb)
                        finally:
                            self._volume.deleteLater()
        finally:
            self._mutex.unlock()
            if is_running:
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
                raise RuntimeError(self.tr("No left channel output selected"))
            if right_device is None:
                raise RuntimeError(self.tr("No right channel output selected"))
            if source_device is None:
                raise RuntimeError(self.tr("No audio input source selected"))
            if left_device == right_device:
                raise RuntimeError(
                    self.tr("Left and right channel outputs cannot use the same device")
                )
            left = QAudioSink(left_device)
            right = QAudioSink(right_device)
            source = QAudioSource(source_device)
            self._split = Split(
                left,
                right,
                source,
                left_latency=self._config.left_latency_ms,
                right_latency=self._config.right_latency_ms,
                left_buffer_time=self._config.left_buffer_time_ms,
                right_buffer_time=self._config.right_buffer_time_ms,
                source_buffer_time=self._config.source_buffer_time_ms,
                parent=self,
            )
            self._split_conn: QMetaObject.Connection = self._split.finished.connect(
                self.__exit__
            )
            self._split(None, None, None)
            if volume is not None:
                self._volume = Volume(left, right, volume, parent=self)
                self._volume_conn: QMetaObject.Connection = (
                    self._volume.finished.connect(self.__exit__)
                )
                self._volume(None, None, None)
        except BaseException as e:
            self.__exit__(type(e), e, e.__traceback__)
            raise
