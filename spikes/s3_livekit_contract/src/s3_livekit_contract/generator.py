"""Synthetic audio-reactive VideoGenerator for spike S3 (RT-02, RT-03, RT-06).

Stands in for a talking-head model so the LiveKit contract can be tested without GPUs.
Each video frame encodes state in its pixels: green = SPEAKING_MARKER while speech audio
plays and IDLE_MARKER otherwise; red = audio level; blue = frame counter.

Pacing comes from the AVSynchronizer in AvatarRunner (bounded queues apply back-pressure),
so the generator yields as fast as it is consumed.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import numpy as np
from livekit import rtc
from livekit.agents.voice.avatar import AudioSegmentEnd, VideoGenerator
from numpy.typing import NDArray

IDLE_MARKER = 0
SPEAKING_MARKER = 255

Output = rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd


class SyntheticVideoGenerator(VideoGenerator):
    def __init__(self, *, width: int, height: int, fps: int, sample_rate: int, num_channels: int = 1) -> None:
        if fps <= 0 or sample_rate % fps:
            raise ValueError("fps must be positive and divide sample_rate exactly")
        self._width = width
        self._height = height
        self._fps = fps
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._samples_per_frame = sample_rate // fps
        self._queue: asyncio.Queue[rtc.AudioFrame | AudioSegmentEnd] = asyncio.Queue()
        self._pending: NDArray[np.int16] = np.zeros(0, dtype=np.int16)
        self._generation = 0
        self._frame_index = 0

    async def push_audio(self, frame: rtc.AudioFrame | AudioSegmentEnd) -> None:
        if isinstance(frame, rtc.AudioFrame) and (
            frame.sample_rate != self._sample_rate or frame.num_channels != self._num_channels
        ):
            raise ValueError(
                f"expected sample_rate={self._sample_rate} num_channels={self._num_channels}, "
                f"got sample_rate={frame.sample_rate} num_channels={frame.num_channels}"
            )
        await self._queue.put(frame)

    def clear_buffer(self) -> None:
        while not self._queue.empty():
            self._queue.get_nowait()
        self._pending = np.zeros(0, dtype=np.int16)
        self._generation += 1

    def __aiter__(self) -> AsyncIterator[Output]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[Output]:
        step = self._samples_per_frame * self._num_channels
        while True:
            if self._queue.empty():
                if self._pending.size == 0:
                    yield self._video_frame(speaking=False, level=0)
                    await asyncio.sleep(0)
                    continue
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=1 / self._fps)
                except TimeoutError:
                    # Audio is arriving slower than real time: keep video moving rather than freeze.
                    yield self._video_frame(speaking=False, level=0)
                    continue
            else:
                item = self._queue.get_nowait()

            generation = self._generation
            if isinstance(item, AudioSegmentEnd):
                if self._pending.size:
                    padding = np.zeros(step - self._pending.size, dtype=np.int16)
                    self._pending = np.concatenate([self._pending, padding])
                    for frame in self._speaking_frames(step, generation):
                        yield frame
                if generation == self._generation:
                    yield AudioSegmentEnd()
                continue

            samples = np.frombuffer(bytes(item.data), dtype=np.int16)
            self._pending = np.concatenate([self._pending, samples])
            for frame in self._speaking_frames(step, generation):
                yield frame

    def _speaking_frames(self, step: int, generation: int) -> Iterator[Output]:
        """Lazily yield (video, audio) per frame; stops as soon as clear_buffer bumps the generation."""
        while self._pending.size >= step and generation == self._generation:
            chunk, self._pending = self._pending[:step], self._pending[step:]
            rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
            yield self._video_frame(speaking=True, level=int(min(255.0, rms / 32768 * 1020)))
            if generation != self._generation:
                return
            yield rtc.AudioFrame(
                chunk.tobytes(), self._sample_rate, self._num_channels, self._samples_per_frame
            )

    def _video_frame(self, *, speaking: bool, level: int) -> rtc.VideoFrame:
        pixels = np.empty((self._height, self._width, 4), dtype=np.uint8)
        pixels[..., 0] = level
        pixels[..., 1] = SPEAKING_MARKER if speaking else IDLE_MARKER
        pixels[..., 2] = self._frame_index % 256
        pixels[..., 3] = 255
        self._frame_index += 1
        return rtc.VideoFrame(self._width, self._height, rtc.VideoBufferType.RGBA, pixels.tobytes())
