from fractions import Fraction
from sys import exc_info, exception
from types import TracebackType
from typing import NamedTuple, Self, cast, override

from av import AudioFormat, AudioFrame, AudioLayout
from av.filter import Graph
from av.filter.context import FilterContext
from PySide6.QtCore import QIODevice, QObject, Signal, Slot
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QAudioSource, QtAudio


class Split(QObject):
    finished = Signal(object, object, object)

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
        self._source: Split._Device = self._handler(source)
        self._left: Split._Device = self._handler(left)
        self._right: Split._Device = self._handler(right)
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
            for target in self._left, self._right, self._source:
                target.device.stop()
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
                        bytes(
                            memoryview(output.planes[0])[: output.samples * target.bpf]
                        )
                    )
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
            if self._source.device.state() != QtAudio.State.StoppedState:
                raise RuntimeError("音频分流正在运行中！")
            self._source_io: QIODevice = self._source.device.start()
            self._ios: tuple[QIODevice, QIODevice] = (
                self._left.device.start(),
                self._right.device.start(),
            )
            self._source_io.readyRead.connect(self._on_ready_read)
        finally:
            if exc_type is not None:
                self.__exit__(exc_type, exc, tb)
            elif exception() is not None:
                self.__exit__(*exc_info())

    @Slot()
    def _on_ready_read(self) -> None:
        try:
            data: bytes = cast(bytes, self._source_io.readAll())
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
                        raise RuntimeError(
                            f"音频输出未完整写入：{written}/{len(payload)}"
                        )
        except BaseException:
            self.__exit__(*exc_info())
            raise
