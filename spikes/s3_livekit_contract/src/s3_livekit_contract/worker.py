"""Spike S3 avatar worker: joins a room and serves the LiveKit avatar contract (RT-06, LK-01, LK-02).

Uses only the public livekit-agents avatar API (no private AvatarRunner arguments) so the
contract is exercised exactly as LiveKit ships it.
"""

from __future__ import annotations

from dataclasses import dataclass

from livekit import rtc
from livekit.agents.voice.avatar import AvatarOptions, AvatarRunner, DataStreamAudioReceiver

from s3_livekit_contract.generator import SyntheticVideoGenerator


@dataclass
class AvatarWorker:
    room: rtc.Room
    runner: AvatarRunner

    async def aclose(self) -> None:
        try:
            await self.runner.aclose()
        finally:
            await self.room.disconnect()


async def start_avatar_worker(
    *, url: str, token: str, agent_identity: str, options: AvatarOptions
) -> AvatarWorker:
    """Connect with an avatar token and start streaming synchronised A/V driven by `agent_identity`."""
    room = rtc.Room()
    await room.connect(url, token, rtc.RoomOptions(auto_subscribe=False))
    receiver = DataStreamAudioReceiver(room, sender_identity=agent_identity)
    generator = SyntheticVideoGenerator(
        width=options.video_width,
        height=options.video_height,
        fps=int(options.video_fps),
        sample_rate=options.audio_sample_rate,
        num_channels=options.audio_channels,
    )
    runner = AvatarRunner(room, audio_recv=receiver, video_gen=generator, options=options)
    await runner.start()
    return AvatarWorker(room=room, runner=runner)
