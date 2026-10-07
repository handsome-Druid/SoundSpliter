from ctypes import POINTER, byref, c_bool, c_int, c_ulong, c_void_p, c_wchar_p, windll
from fractions import Fraction
from logging import Logger, getLogger
from types import MethodType, TracebackType
from typing import ClassVar, NamedTuple, Self, cast, override

from av import AudioFormat, AudioFrame, AudioLayout
from av.filter import Graph
from av.filter.context import FilterContext
from PySide6.QtCore import (
    QIODevice,
    QMetaObject,
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QAudioSource, QtAudio
from shiboken6 import isValid


class Split(QObject):
    finished = Signal(object, object, object)
    _logger: Logger = getLogger(name=__name__)
    _channel_names: ClassVar[list[str]] = ["左声道输出", "右声道输出"]
    _source_io: QIODevice
    _ios: tuple[QIODevice, QIODevice]

    class _Thread(QThread):
        @override
        def __init__(self, /, parent: QObject | None = None) -> None:
            super().__init__(parent)

        @override
        def run(self) -> None:
            windll.avrt.AvSetMmThreadCharacteristicsW.restype = c_void_p
            windll.avrt.AvSetMmThreadCharacteristicsW.argtypes = [
                c_wchar_p,
                POINTER(cls=c_ulong),
            ]
            windll.avrt.AvSetMmThreadPriority.restype = c_bool
            windll.avrt.AvSetMmThreadPriority.argtypes = [c_void_p, c_int]
            handle = windll.avrt.AvSetMmThreadCharacteristicsW(
                "Pro Audio", byref(c_ulong())
            )
            if not handle:
                Split._logger.warning(msg="MMCSS 注册失败，线程将按普通优先级运行")
                self._handle = None
            else:
                self._handle = c_void_p(handle)
                if not windll.avrt.AvSetMmThreadPriority(self._handle, 2):
                    Split._logger.warning(msg="MMCSS 线程优先级设置失败")
            try:
                super().run()
            finally:
                if self._handle is not None:
                    windll.avrt.AvRevertMmThreadCharacteristics.restype = c_bool
                    windll.avrt.AvRevertMmThreadCharacteristics.argtypes = [c_void_p]
                    windll.avrt.AvRevertMmThreadCharacteristics(self._handle)

    class _Timer(QObject):
        finished = Signal(object, object, object)

        @override
        def __init__(
            self,
            /,
            func: MethodType,
            finalizer: MethodType,
            parent: QObject | None = None,
            *,
            objectName: str | None = None,
        ) -> None:
            super().__init__(parent, objectName=objectName)
            self._timer = QTimer(parent=self)
            self._timer.setInterval(1)
            self._timer.timeout.connect(self._on_timeout)
            self._func: MethodType = func
            self._finalizer: MethodType = finalizer

        @Slot()
        def _on_timeout(self) -> None:
            if self.thread().isInterruptionRequested():
                self.__exit__(None, None, None)
            else:
                try:
                    self._func()
                except BaseException as e:
                    self.__exit__(type(e), e, e.__traceback__)
                    raise

        @Slot(object, object, object)
        def __call__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
            /,
        ) -> None:
            if exc_type is not None:
                self.__exit__(exc_type, exc, tb)
            else:
                self._timer.start()

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
            self._timer.stop()
            try:
                self._finalizer()
            finally:
                self.thread().quit()
                self.finished.emit(exc_type, exc, tb)

    class _Device(NamedTuple):
        device: QAudioSource | QAudioSink
        rate: int
        format: AudioFormat
        layout: AudioLayout
        bpf: int

    @staticmethod
    def _handler(
        device: QAudioSource | QAudioSink,
        /,
    ) -> Split._Device:
        fmt: QAudioFormat = device.format()
        rate: int = fmt.sampleRate()
        format: AudioFormat = AudioFormat(
            name=fmt.sampleFormat()
            .name.replace("UInt", "u")
            .replace("Int", "s")
            .replace("Float", "flt")
        )
        layout: AudioLayout = AudioLayout(
            layout=fmt.channelConfig()
            .name.removeprefix("ChannelConfig")
            .removeprefix("Surround")
            .replace("Dot", ".")
            .lower()
        )
        bpf: int = fmt.bytesPerFrame()
        return Split._Device(device, rate, format, layout, bpf)

    @override
    def __init__(
        self,
        /,
        left: QAudioSink,
        right: QAudioSink,
        source: QAudioSource,
        left_latency: int = 0,
        right_latency: int = 0,
        parent: QObject | None = None,
        *,
        objectName: str | None = None,
    ) -> None:
        super().__init__(parent, objectName=objectName)
        self._thread = self._Thread(parent=self)
        self._source: Split._Device = self._handler(source)
        self._left: Split._Device = self._handler(left)
        self._right: Split._Device = self._handler(right)
        self._left.device.setBufferFrameCount(self._left.rate * 30 // 1000)
        self._right.device.setBufferFrameCount(self._right.rate * 30 // 1000)
        self._source.device.setBufferFrameCount(self._source.rate * 20 // 1000)
        self._source.device.stateChanged.connect(self._on_state_changed)
        graph: Graph = Graph()
        self._input: FilterContext = graph.add_abuffer(
            sample_rate=self._source.rate,
            format=self._source.format.name,
            layout=self._source.layout.name,
            time_base=Fraction(numerator=1, denominator=self._source.rate),
        )
        mix: FilterContext = graph.add(
            filter="aformat",
            sample_rates=str(object=self._source.rate),
            sample_fmts=self._source.format.planar.name,
            channel_layouts="stereo",
        )
        splitter: FilterContext = graph.add(
            filter="channelsplit", args="channel_layout=stereo"
        )
        self._input.link_to(input_=mix)
        mix.link_to(input_=splitter)
        self._sinks: tuple[FilterContext, FilterContext] = (
            graph.add(filter="abuffersink"),
            graph.add(filter="abuffersink"),
        )
        for index, (target, latency) in enumerate(
            iterable=zip(
                (self._left, self._right),
                (left_latency, right_latency),
                strict=True,
            )
        ):
            resample: FilterContext = graph.add(filter="aresample", ichl="mono")
            format: FilterContext = graph.add(
                filter="aformat",
                sample_rates=str(object=target.rate),
                sample_fmts=target.format.name,
                channel_layouts=target.layout.name,
            )
            if latency > 0:
                delay: FilterContext = graph.add(
                    filter="adelay",
                    delays=str(latency),
                    all="1",
                )
                splitter.link_to(input_=delay, output_idx=index, input_idx=0)
                delay.link_to(input_=resample)
            else:
                splitter.link_to(input_=resample, output_idx=index, input_idx=0)
            resample.link_to(input_=format)
            format.link_to(input_=self._sinks[index])
        graph.configure()

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
            self._source.device.stop()
            if (
                hasattr(self, "_timer_conn")
                and hasattr(self, "_timer")
                and isValid(self._timer)
            ):
                self._timer.finished.disconnect(self._timer_conn)
            if hasattr(self, "_thread_conn"):
                self._thread.started.disconnect(self._thread_conn)
            self._thread.requestInterruption()
            if not self._thread.wait(1000):
                self._thread.finished.connect(self._thread.deleteLater)
                self._thread = self._Thread(parent=self)
        finally:
            try:
                for target in self._left, self._right:
                    target.device.stop()
            finally:
                self.finished.emit(exc_type, exc, tb)

    def _finalize(self):
        if not hasattr(self, "_ios"):
            return
        self._input.push(frame=None)
        for index, target in enumerate(iterable=(self._left, self._right)):
            while True:
                try:
                    output: AudioFrame = cast(AudioFrame, self._sinks[index].pull())
                except EOFError:
                    break
                self._ios[index].write(
                    bytes(memoryview(output.planes[0])[: output.samples * target.bpf])
                )

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
            if (
                self._source.device.state() != QtAudio.State.StoppedState
                and self._thread.isRunning()
            ):
                return
            elif self._thread.isRunning() ^ (
                self._source.device.state() != QtAudio.State.StoppedState
            ):
                raise RuntimeError("上次退出清理没有完成；正在尝试重新清理")
            self._source_io: QIODevice = self._source.device.start()
            self._source_io.moveToThread(self._thread)
            self._ios: tuple[QIODevice, QIODevice] = (
                self._left.device.start(),
                self._right.device.start(),
            )
            for io in self._ios:
                io.moveToThread(self._thread)
            self._timer = self._Timer(
                func=self._on_ready_read, finalizer=self._finalize
            )
            self._timer.moveToThread(self._thread)
            self._timer_conn: QMetaObject.Connection = self._timer.finished.connect(
                self.__exit__
            )
            self._thread_conn: QMetaObject.Connection = self._thread.started.connect(
                lambda: self._timer(None, None, None),
                type=Qt.ConnectionType.DirectConnection,
            )
            self._thread.finished.connect(self._timer.deleteLater)
            self._thread.start()
        except BaseException as e:
            self.__exit__(type(e), e, e.__traceback__)
            raise

    @Slot(QtAudio.State)
    def _on_state_changed(self, state: QtAudio.State) -> None:
        if state == QtAudio.State.IdleState:
            self._logger.warning(msg="输入源缓冲区已满，音频数据已被丢弃")

    # @Slot()
    def _on_ready_read(self) -> None:
        try:
            data: bytes = cast(bytes, self._source_io.readAll())
            if not data:
                return
            frame: AudioFrame = AudioFrame(
                format=self._source.format,
                layout=self._source.layout,
                samples=len(data) // self._source.bpf,
            )
            frame.sample_rate = self._source.rate
            memoryview(frame.planes[0])[:] = memoryview(data)
            self._input.push(frame=frame)
            for index, target in enumerate(iterable=(self._left, self._right)):
                while True:
                    try:
                        output: AudioFrame = cast(AudioFrame, self._sinks[index].pull())
                    except BlockingIOError:
                        break
                    payload: bytes = bytes(
                        memoryview(output.planes[0])[: output.samples * target.bpf]
                    )
                    written: int = self._ios[index].write(payload)
                    if written != len(payload):
                        self._logger.warning(
                            msg=f"{self._channel_names[index]}发生音频短写：{written} / {len(payload)} bytes"
                        )
        except BaseException as e:
            self.__exit__(type(e), e, e.__traceback__)
            raise
