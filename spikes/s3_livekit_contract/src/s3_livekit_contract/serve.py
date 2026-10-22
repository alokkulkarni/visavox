"""Stand-in avatar process for the local cell (NFR-O5, SDD §14; RT-06, LK-04).

Joins one LiveKit room with a room-scoped avatar token and serves the avatar contract for one agent
identity until SIGTERM or SIGINT. Writes READY_FILE once joined so the compose healthcheck can see it.
LK1 replaces this with services/avatar-engine.
"""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from livekit.agents.voice.avatar import AvatarOptions

from s3_livekit_contract.tokens import avatar_token
from s3_livekit_contract.worker import start_avatar_worker

OPTIONS = AvatarOptions(
    video_width=640, video_height=360, video_fps=25, audio_sample_rate=24_000, audio_channels=1
)
REQUIRED = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "AVATAR_ROOM", "AGENT_IDENTITY")


class RoomClosedError(RuntimeError):
    """LiveKit closed the avatar's room. The process exits so Docker's restart policy rejoins it."""


class Closeable(Protocol):
    async def aclose(self) -> None: ...


StartWorker = Callable[..., Awaitable[Closeable]]


@dataclass(frozen=True)
class ServeConfig:
    url: str
    api_key: str
    api_secret: str = field(repr=False)
    room: str
    agent_identity: str
    avatar_identity: str
    ready_file: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ServeConfig:
        missing = [name for name in REQUIRED if not env.get(name)]
        if missing:
            raise ValueError(f"missing environment variables: {', '.join(missing)}")
        return cls(
            url=env["LIVEKIT_URL"],
            api_key=env["LIVEKIT_API_KEY"],
            api_secret=env["LIVEKIT_API_SECRET"],
            room=env["AVATAR_ROOM"],
            agent_identity=env["AGENT_IDENTITY"],
            avatar_identity=env.get("AVATAR_IDENTITY") or "local-avatar",
            ready_file=Path(env.get("READY_FILE") or "/tmp/avatar-ready"),  # noqa: S108 - container-local marker
        )


async def serve(
    config: ServeConfig, stop: asyncio.Event, *, start: StartWorker = start_avatar_worker
) -> None:
    """Join the room, report ready, and serve until `stop` is set.

    Ready means joined and waiting for the agent, which may arrive much later. A failed start, or LiveKit
    closing the room (it does once only agents remain), ends serving with an error, so the container exits
    and Docker restarts it. The worker is always closed.
    """
    token = avatar_token(
        api_key=config.api_key,
        api_secret=config.api_secret,
        room=config.room,
        avatar_identity=config.avatar_identity,
        agent_identity=config.agent_identity,
    )
    disconnected = asyncio.Event()
    starting = asyncio.ensure_future(
        start(
            url=config.url,
            token=token,
            agent_identity=config.agent_identity,
            options=OPTIONS,
            on_joined=lambda: config.ready_file.write_text("ready\n"),
            on_disconnected=disconnected.set,
        )
    )
    stopping = asyncio.ensure_future(stop.wait())
    dropped = asyncio.ensure_future(disconnected.wait())
    worker: Closeable | None = None
    try:
        done, _ = await asyncio.wait({starting, stopping, dropped}, return_when=asyncio.FIRST_COMPLETED)
        if starting in done:
            worker = starting.result()
            done, _ = await asyncio.wait({stopping, dropped}, return_when=asyncio.FIRST_COMPLETED)
        if stopping not in done:
            raise RoomClosedError("LiveKit closed the room; exiting so the container restarts and rejoins")
    finally:
        config.ready_file.unlink(missing_ok=True)
        stopping.cancel()
        dropped.cancel()
        if worker is not None:
            await worker.aclose()
        elif not starting.done():
            starting.cancel()
            await asyncio.gather(starting, return_exceptions=True)


def main() -> None:
    config = ServeConfig.from_env(os.environ)

    async def run() -> Any:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await serve(config, stop)

    asyncio.run(run())


if __name__ == "__main__":
    main()
