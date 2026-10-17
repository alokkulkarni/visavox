"""LiveKit virtual-avatar contract (SDD §7.3): a stock LiveKit agent drives the Visavox avatar worker.

Requirements: RT-02, RT-03, RT-06, LK-01, LK-02, LK-04, NFR-L5, NFR-Q1.
Kept after spike S3: LK1 runs this suite unchanged against services/avatar-engine.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from livekit import rtc

from .conftest import ContractSession, connect, record, send_segment, wait_for

pytestmark = pytest.mark.contract

PUBLISH_ON_BEHALF = "lk.publish_on_behalf"


async def test_avatar_joins_as_agent_publishing_on_behalf_of_the_agent(session: ContractSession) -> None:
    """LK-04, RT-06."""
    await wait_for(lambda: session.avatar() is not None)
    avatar = session.avatar()
    assert avatar is not None
    assert avatar.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
    assert avatar.attributes.get(PUBLISH_ON_BEHALF) == session.agent_identity


async def test_avatar_publishes_camera_and_microphone_tracks(session: ContractSession) -> None:
    """RT-02."""

    def sources() -> set[int]:
        avatar = session.avatar()
        return {pub.source for pub in avatar.track_publications.values()} if avatar else set()

    await wait_for(
        lambda: {rtc.TrackSource.SOURCE_CAMERA, rtc.TrackSource.SOURCE_MICROPHONE} <= sources(), timeout=15.0
    )


async def test_video_keeps_flowing_while_the_avatar_is_silent(session: ContractSession) -> None:
    """RT-02, NFR-Q1: idle motion, never a frozen track."""
    watcher = await session.watch_video()
    t0 = time.monotonic()
    await asyncio.sleep(2.0)
    frames = watcher.since(t0)
    record("idle_fps_at_viewer", len(frames) / 2.0)
    assert len(frames) >= 40
    assert not any(speaking for _, speaking in frames)


async def test_segment_reports_playback_finished_with_its_duration(session: ContractSession) -> None:
    """RT-06: playback_started / playback_finished RPCs flow back to the agent."""
    await send_segment(session.audio_out, 1.0)
    event = await asyncio.wait_for(session.audio_out.wait_for_playout(), timeout=15.0)
    assert event.interrupted is False
    assert event.playback_position == pytest.approx(1.0, abs=0.15)


async def test_clear_buffer_interrupts_within_300_ms(session: ContractSession) -> None:
    """RT-03, NFR-L5: barge-in stops the avatar fast."""
    started = asyncio.Event()
    session.audio_out.on("playback_started", lambda _ev: started.set())
    await send_segment(session.audio_out, 3.0)
    await asyncio.wait_for(started.wait(), timeout=15.0)
    await asyncio.sleep(0.5)

    t0 = time.monotonic()
    session.audio_out.clear_buffer()
    event = await asyncio.wait_for(session.audio_out.wait_for_playout(), timeout=5.0)
    elapsed = time.monotonic() - t0
    record("clear_buffer_to_playback_finished_ms", elapsed * 1000)

    assert event.interrupted is True
    assert elapsed <= 0.3


async def test_first_speaking_frame_reaches_the_viewer_quickly(session: ContractSession) -> None:
    """Transport and synchroniser share of NFR-L3 (model time is zero with the synthetic generator)."""
    watcher = await session.watch_video()
    t0 = time.monotonic()
    await send_segment(session.audio_out, 1.0)
    first = await watcher.first_speaking_after(t0)
    record("first_audio_to_first_speaking_frame_ms", (first - t0) * 1000)
    assert first - t0 <= 0.5


async def test_clear_buffer_from_an_unexpected_identity_is_rejected(session: ContractSession) -> None:
    """LK-04: only the paired agent may control the avatar."""
    rogue = await connect(f"rogue-{uuid.uuid4().hex[:8]}", session.room_name)
    try:
        await wait_for(lambda: session.avatar_identity in rogue.remote_participants)
        try:
            response = await rogue.local_participant.perform_rpc(
                destination_identity=session.avatar_identity, method="lk.clear_buffer", payload=""
            )
        except rtc.RpcError:
            response = "rpc-error"
        assert response != "ok"
    finally:
        await rogue.disconnect()
