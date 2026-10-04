from array import array
from fractions import Fraction
from random import Random
from unittest.mock import Mock

import pytest
from av import AudioFrame, AudioResampler
from av.filter import Graph
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QAudioSource, QtAudio

from ss.external.split import Split


@pytest.mark.parametrize("source_format", ["u8", "s16", "s32", "flt"])
@pytest.mark.parametrize("source_layout", ["stereo", "5.1"])
@pytest.mark.parametrize("target_format", ["u8", "s16", "s32", "flt"])
@pytest.mark.parametrize("mixed_rates", [False, True])
def test_fused_graph_matches_separate_graphs(
    source_format: str,
    source_layout: str,
    target_format: str,
    mixed_rates: bool,
) -> None:
    formats = {
        "u8": QAudioFormat.SampleFormat.UInt8,
        "s16": QAudioFormat.SampleFormat.Int16,
        "s32": QAudioFormat.SampleFormat.Int32,
        "flt": QAudioFormat.SampleFormat.Float,
    }
    configs = {
        "mono": QAudioFormat.ChannelConfig.ChannelConfigMono,
        "stereo": QAudioFormat.ChannelConfig.ChannelConfigStereo,
        "5.1": QAudioFormat.ChannelConfig.ChannelConfigSurround5Dot1,
    }
    rates = (44100, 32000) if mixed_rates else (48000, 48000)
    layouts = ("stereo", "5.1") if mixed_rates else ("mono", "mono")
    source = Mock(spec=QAudioSource)
    source.state.return_value = QtAudio.State.StoppedState
    source_io = Mock(spec=QIODevice)
    source.start.return_value = source_io
    targets = (Mock(spec=QAudioSink), Mock(spec=QAudioSink))
    buffers = (QBuffer(), QBuffer())
    for device, name, layout, rate in (
        (source, source_format, source_layout, 48000),
        (targets[0], target_format, layouts[0], rates[0]),
        (targets[1], target_format, layouts[1], rates[1]),
    ):
        fmt = QAudioFormat()
        fmt.setSampleFormat(formats[name])
        fmt.setChannelConfig(configs[layout])
        fmt.setSampleRate(rate)
        device.format.return_value = fmt
    for target, buffer in zip(targets, buffers, strict=True):
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        target.start.return_value = buffer
    split = Split(targets[0], targets[1], source)
    split(None, None, None)

    source_resampler = AudioResampler(
        format=source_format + "p", layout="stereo", rate=48000
    )
    target_resamplers = tuple(
        AudioResampler(
            format=target_format, layout=layout, rate=rate, options={"ichl": "mono"}
        )
        for layout, rate in zip(layouts, rates, strict=True)
    )
    graph = Graph()
    input = graph.add_abuffer(
        sample_rate=48000,
        format=source_format + "p",
        layout="stereo",
        time_base=Fraction(1, 48000),
    )
    channelsplit = graph.add("channelsplit", "channel_layout=stereo")
    sinks = (graph.add("abuffersink"), graph.add("abuffersink"))
    input.link_to(channelsplit)
    for index, sink in enumerate(sinks):
        channelsplit.link_to(sink, index, 0)
    graph.configure()
    expected = (bytearray(), bytearray())
    rng = Random(17)
    for samples in (1, 7, 127, 256, 511):
        frame = AudioFrame(format=source_format, layout=source_layout, samples=samples)
        frame.sample_rate = 48000
        if source_format == "flt":
            memoryview(frame.planes[0]).cast("f")[:] = array(
                "f",
                (
                    rng.uniform(-0.2, 0.2)
                    for _ in range(samples * len(frame.layout.channels))
                ),
            )
        else:
            memoryview(frame.planes[0])[:] = rng.randbytes(frame.planes[0].buffer_size)
        source_io.readAll.return_value = QByteArray(bytes(frame.planes[0]))
        split._on_ready_read()
        for stereo in source_resampler.resample(frame):
            input.push(stereo)
            for index, (sink, resampler) in enumerate(
                zip(sinks, target_resamplers, strict=True)
            ):
                for output in resampler.resample(sink.pull()):
                    expected[index].extend(
                        memoryview(output.planes[0])[
                            : output.samples
                            * len(output.layout.channels)
                            * output.format.bytes
                        ]
                    )
    assert not source_resampler.resample(None)
    input.push(None)
    for index, resampler in enumerate(target_resamplers):
        for output in resampler.resample(None):
            expected[index].extend(
                memoryview(output.planes[0])[
                    : output.samples * len(output.layout.channels) * output.format.bytes
                ]
            )
    split.__exit__(None, None, None)
    assert tuple(bytes(buffer.data()) for buffer in buffers) == tuple(
        bytes(data) for data in expected
    )
    source.stop.assert_called_once()
    for target in targets:
        target.stop.assert_called_once()
