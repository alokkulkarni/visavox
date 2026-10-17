"""Synthetic audio-reactive generator standing in for a face model in S3 (RT-02, RT-03, RT-06).

Frames encode state in pixels so a remote viewer can tell idle from speaking frames:
green channel = SPEAKING_MARKER while speech audio plays, IDLE_MARKER otherwise.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import numpy as np
import pytest
from livekit import rtc
from livekit.agents.voice.avatar import AudioSegmentEnd

from s3_livekit_contract.generator import IDLE_MARKER, SPEAKING_MARKER, SyntheticVideoGenerator

SR = 24_000
FPS = 25
CHUNK = SR // FPS
W, H = 64, 36

Item = rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd


def pcm(seconds: float, sample_rate: int = SR, value: int = 8_000) -> rtc.AudioFrame:
    samples = int(sample_rate * seconds)
    data = np.full(samples, value, dtype=np.int16).tobytes()
    return rtc.AudioFrame(data, sample_rate, 1, samples)


def generator() -> SyntheticVideoGenerator:
    return SyntheticVideoGenerator(width=W, height=H, fps=FPS, sample_rate=SR, num_channels=1)


async def take(stream: AsyncIterator[Item], count: int) -> list[Item]:
    async def _collect() -> list[Item]:
        return [await anext(stream) for _ in range(count)]

    return await asyncio.wait_for(_collect(), timeout=2.0)


async def take_segment(stream: AsyncIterator[Item]) -> list[Item]:
    async def _collect() -> list[Item]:
        items: list[Item] = []
        while not items or not isinstance(items[-1], AudioSegmentEnd):
            items.append(await anext(stream))
        return items

    return await asyncio.wait_for(_collect(), timeout=2.0)


def marker(frame: Item) -> int:
    assert isinstance(frame, rtc.VideoFrame)
    pixels = np.frombuffer(bytes(frame.data), dtype=np.uint8).reshape(frame.height, frame.width, 4)
    return int(pixels[frame.height // 2, frame.width // 2, 1])


async def test_emits_idle_rgba_frames_of_configured_size_when_no_audio_is_queued() -> None:
    items = await take(aiter(generator()), 5)
    for item in items:
        assert isinstance(item, rtc.VideoFrame)
        assert (item.width, item.height, item.type) == (W, H, rtc.VideoBufferType.RGBA)
        assert marker(item) == IDLE_MARKER


async def test_one_second_segment_yields_matching_audio_and_speaking_video_then_segment_end() -> None:
    gen = generator()
    await gen.push_audio(pcm(1.0))
    await gen.push_audio(AudioSegmentEnd())
    items = await take_segment(aiter(gen))
    audio = [i for i in items if isinstance(i, rtc.AudioFrame)]
    video = [i for i in items if isinstance(i, rtc.VideoFrame)]
    assert sum(a.samples_per_channel for a in audio) == SR
    assert all(a.samples_per_channel == CHUNK for a in audio)
    assert len(video) == FPS
    assert all(marker(v) == SPEAKING_MARKER for v in video)
    assert isinstance(items[-1], AudioSegmentEnd)


async def test_video_and_audio_frames_alternate_so_each_frame_has_its_audio() -> None:
    gen = generator()
    await gen.push_audio(pcm(0.2))
    await gen.push_audio(AudioSegmentEnd())
    kinds = [type(i).__name__ for i in await take_segment(aiter(gen))]
    assert kinds == ["VideoFrame", "AudioFrame"] * 5 + ["AudioSegmentEnd"]


async def test_partial_final_chunk_is_padded_to_a_whole_video_frame() -> None:
    gen = generator()
    await gen.push_audio(pcm(0.05))
    await gen.push_audio(AudioSegmentEnd())
    items = await take_segment(aiter(gen))
    audio = [i for i in items if isinstance(i, rtc.AudioFrame)]
    assert [a.samples_per_channel for a in audio] == [CHUNK, CHUNK]
    assert sum(1 for i in items if isinstance(i, rtc.VideoFrame)) == 2


async def test_clear_buffer_discards_queued_audio_and_stays_idle() -> None:
    gen = generator()
    await gen.push_audio(pcm(2.0))
    await gen.push_audio(AudioSegmentEnd())
    gen.clear_buffer()
    items = await take(aiter(gen), 5)
    assert all(isinstance(i, rtc.VideoFrame) and marker(i) == IDLE_MARKER for i in items)


async def test_clear_buffer_mid_segment_returns_to_idle_on_the_next_frame() -> None:
    gen = generator()
    await gen.push_audio(pcm(2.0))
    await gen.push_audio(AudioSegmentEnd())
    stream = aiter(gen)
    before = await take(stream, 4)
    assert marker(before[0]) == SPEAKING_MARKER
    gen.clear_buffer()
    after = await take(stream, 3)
    assert all(isinstance(i, rtc.VideoFrame) and marker(i) == IDLE_MARKER for i in after)


async def test_audio_arriving_slower_than_real_time_does_not_freeze_video() -> None:
    gen = generator()
    await gen.push_audio(pcm(0.02))  # half a video frame, no segment end yet
    items = await take(aiter(gen), 3)
    assert all(isinstance(i, rtc.VideoFrame) for i in items)


async def test_mismatched_audio_format_is_rejected() -> None:
    with pytest.raises(ValueError, match="sample_rate"):
        await generator().push_audio(pcm(0.1, sample_rate=16_000))


@pytest.mark.parametrize(("fps", "sample_rate"), [(0, SR), (7, SR)])
def test_invalid_timing_configuration_is_rejected(fps: int, sample_rate: int) -> None:
    with pytest.raises(ValueError, match="fps"):
        SyntheticVideoGenerator(width=W, height=H, fps=fps, sample_rate=sample_rate)
