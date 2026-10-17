"""Fixtures for the LiveKit avatar contract suite (SDD §7.3; spike S3, kept for LK1).

Needs a LiveKit server. Configure with LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET
(defaults match `livekit-server --dev`). Measurements are appended as JSON lines to
S3_RESULTS_PATH when it is set.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import os
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

import numpy as np
import pytest
from livekit import api, rtc
from livekit.agents.voice.avatar import AvatarOptions, DataStreamAudioOutput

from s3_livekit_contract.generator import SPEAKING_MARKER
from s3_livekit_contract.tokens import avatar_token
from s3_livekit_contract.worker import AvatarWorker, start_avatar_worker

URL = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
KEY = os.environ.get("LIVEKIT_API_KEY", "devkey")
SECRET = os.environ.get("LIVEKIT_API_SECRET", "secret")
SAMPLE_RATE = 24_000
OPTIONS = AvatarOptions(
    video_width=640, video_height=360, video_fps=25, audio_sample_rate=SAMPLE_RATE, audio_channels=1
)


def record(name: str, value: float) -> None:
    path = os.environ.get("S3_RESULTS_PATH")
    if path:
        with open(path, "a") as fh:
            fh.write(json.dumps({"metric": name, "value": round(value, 1)}) + "\n")


async def wait_for(predicate: Callable[[], bool], timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError("condition not met in time")
        await asyncio.sleep(0.05)


async def connect(identity: str, room: str, *, kind: str = "standard") -> rtc.Room:
    token = (
        api.AccessToken(KEY, SECRET)
        .with_identity(identity)
        .with_kind(kind)  # type: ignore[arg-type]
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )
    room_ = rtc.Room()
    await room_.connect(URL, token)
    return room_


def sine_frames(seconds: float, chunk_ms: int = 100) -> list[rtc.AudioFrame]:
    per_chunk = SAMPLE_RATE * chunk_ms // 1000
    total = int(SAMPLE_RATE * seconds)
    t = np.arange(total) / SAMPLE_RATE
    samples = (np.sin(2 * math.pi * 440 * t) * 8_000).astype(np.int16)
    return [
        rtc.AudioFrame(chunk.tobytes(), SAMPLE_RATE, 1, len(chunk))
        for chunk in np.split(samples, range(per_chunk, total, per_chunk))
    ]


async def send_segment(output: DataStreamAudioOutput, seconds: float) -> None:
    for frame in sine_frames(seconds):
        await output.capture_frame(frame)
    output.flush()


@dataclass
class FrameWatcher:
    """Viewer-side record of (arrival time, speaking?) for every avatar video frame."""

    frames: list[tuple[float, bool]] = field(default_factory=list)
    task: asyncio.Task[None] | None = None

    async def run(self, track: rtc.Track) -> None:
        async for event in rtc.VideoStream(track):
            rgba = event.frame.convert(rtc.VideoBufferType.RGBA)
            pixels = np.frombuffer(bytes(rgba.data), dtype=np.uint8).reshape(rgba.height, rgba.width, 4)
            green = int(pixels[rgba.height // 2, rgba.width // 2, 1])
            self.frames.append((time.monotonic(), green > SPEAKING_MARKER // 2))

    def since(self, t0: float) -> list[tuple[float, bool]]:
        return [f for f in self.frames if f[0] >= t0]

    async def first_speaking_after(self, t0: float, timeout: float = 10.0) -> float:
        await wait_for(lambda: any(speaking for _, speaking in self.since(t0)), timeout)
        return next(t for t, speaking in self.since(t0) if speaking)


@dataclass
class ContractSession:
    room_name: str
    agent_identity: str
    avatar_identity: str
    agent_room: rtc.Room
    viewer_room: rtc.Room
    audio_out: DataStreamAudioOutput
    worker: AvatarWorker
    watchers: list[FrameWatcher] = field(default_factory=list)

    def avatar(self) -> rtc.RemoteParticipant | None:
        return self.viewer_room.remote_participants.get(self.avatar_identity)

    async def watch_video(self) -> FrameWatcher:
        def video_track() -> rtc.Track | None:
            participant = self.avatar()
            for pub in participant.track_publications.values() if participant else []:
                if pub.kind == rtc.TrackKind.KIND_VIDEO and pub.track is not None:
                    return pub.track
            return None

        await wait_for(lambda: video_track() is not None, timeout=15.0)
        track = video_track()
        assert track is not None
        watcher = FrameWatcher()
        watcher.task = asyncio.create_task(watcher.run(track))
        self.watchers.append(watcher)
        await wait_for(lambda: len(watcher.frames) > 0, timeout=10.0)
        return watcher


async def _bounded[T](step: str, awaitable: Awaitable[T], seconds: float) -> T:
    """Await one setup or teardown step; a hang fails with the step's name instead of blocking CI."""
    try:
        async with asyncio.timeout(seconds):
            return await awaitable
    except TimeoutError as exc:
        raise TimeoutError(f"{step} did not finish within {seconds:.0f} s") from exc


@pytest.fixture
async def session() -> AsyncIterator[ContractSession]:
    suffix = uuid.uuid4().hex[:8]
    room_name, agent, avatar = f"s3-{suffix}", f"agent-{suffix}", f"avatar-{suffix}"
    agent_room = await _bounded("agent connect", connect(agent, room_name, kind="agent"), 15)
    viewer_room = await _bounded("viewer connect", connect(f"viewer-{suffix}", room_name), 15)
    worker = await _bounded(
        "avatar worker start",
        start_avatar_worker(
            url=URL,
            token=avatar_token(
                api_key=KEY, api_secret=SECRET, room=room_name, avatar_identity=avatar, agent_identity=agent
            ),
            agent_identity=agent,
            options=OPTIONS,
        ),
        30,
    )
    audio_out = DataStreamAudioOutput(
        agent_room,
        destination_identity=avatar,
        sample_rate=SAMPLE_RATE,
        wait_remote_track=rtc.TrackKind.KIND_VIDEO,
        wait_playback_start=True,
    )
    contract = ContractSession(room_name, agent, avatar, agent_room, viewer_room, audio_out, worker)
    yield contract

    for watcher in contract.watchers:
        if watcher.task is not None:
            watcher.task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await _bounded("frame watcher stop", watcher.task, 5)
    await _bounded("avatar worker close", worker.aclose(), 15)
    await _bounded("agent disconnect", agent_room.disconnect(), 10)
    await _bounded("viewer disconnect", viewer_room.disconnect(), 10)
