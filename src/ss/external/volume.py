from types import TracebackType
from typing import Self, override

from pycaw.callbacks import AudioEndpointVolumeCallback
from pycaw.constants import DEVICE_STATE, EDataFlow
from pycaw.utils import AudioDevice, AudioUtilities
from PySide6.QtCore import QMutex, QObject, Qt, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioSink


class Volume(QObject):
    finished = Signal(object, object, object)
    _notify = Signal(object)
    _mutex = QMutex()

    class _Callback(AudioEndpointVolumeCallback):
        @override
        def __init__(self, left: QAudioSink, right: QAudioSink, parent: Volume) -> None:
            super().__init__()
            self._left: QAudioSink = left
            self._right: QAudioSink = right
            self._parent: Volume = parent

        @override
        def on_notify(
            self,
            new_volume: float,
            new_mute: int,
            event_context: object,
            channels: int,
            channel_volumes: list[float],
        ) -> None:
            try:
                self._parent._notify.emit(0.0 if new_mute else new_volume)
            except BaseException as e:
                self._parent._notify.emit(e)
                raise

    @Slot(object)
    def _on_notify(
        self,
        gain: float | BaseException,
    ) -> None:
        if isinstance(gain, BaseException):
            self.__exit__(type(gain), gain, gain.__traceback__)
        else:
            try:
                self._left.setVolume(gain)
                self._right.setVolume(gain)
            except BaseException as e:
                self.__exit__(type(e), e, e.__traceback__)
                raise

    @override
    def __init__(
        self,
        /,
        left: QAudioSink,
        right: QAudioSink,
        volume: QAudioDevice,
        parent: QObject | None = None,
        *,
        objectName: str | None = None,
    ) -> None:
        super().__init__(parent, objectName=objectName)
        self._left: QAudioSink = left
        self._right: QAudioSink = right
        self._device: AudioDevice = next(
            device
            for device in AudioUtilities.GetAllDevices(
                data_flow=EDataFlow.eRender.value,
                device_state=DEVICE_STATE.ACTIVE.value,
            )
            if device.id == bytes(volume.id().data()).decode()
        )
        self._notify.connect(self._on_notify, type=Qt.ConnectionType.QueuedConnection)
        self._callback = self._Callback(left, right, parent=self)

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
            try:
                self._device.EndpointVolume.RegisterControlChangeNotify(self._callback)
            except BaseException:
                self._mutex.unlock()
                raise
            gain: float = (
                0.0
                if self._device.EndpointVolume.GetMute()
                else float(self._device.EndpointVolume.GetMasterVolumeLevelScalar())
            )
            self._left.setVolume(gain)
            self._right.setVolume(gain)
        except BaseException as e:
            self.__exit__(type(e), e, e.__traceback__)
            raise

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
            if not self._mutex.try_lock():
                self._device.EndpointVolume.UnregisterControlChangeNotify(
                    self._callback
                )
            self._mutex.unlock()
        finally:
            self.finished.emit(exc_type, exc, tb)
