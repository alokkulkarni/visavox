"""AvatarWorker shutdown always releases its room (RT-06, LK-01; S3 finding 4, issue #9)."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from s3_livekit_contract import worker as worker_module
from s3_livekit_contract.serve import OPTIONS
from s3_livekit_contract.worker import AvatarWorker


class FakeRunner:
    def __init__(self, calls: list[str], error: Exception | None = None) -> None:
        self._calls = calls
        self._error = error

    async def aclose(self) -> None:
        self._calls.append("runner.aclose")
        if self._error is not None:
            raise self._error


class FakeRoom:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def disconnect(self) -> None:
        self._calls.append("room.disconnect")


def worker(calls: list[str], error: Exception | None = None) -> AvatarWorker:
    return AvatarWorker(room=cast(Any, FakeRoom(calls)), runner=cast(Any, FakeRunner(calls, error)))


async def test_aclose_stops_the_runner_then_leaves_the_room() -> None:
    calls: list[str] = []
    await worker(calls).aclose()
    assert calls == ["runner.aclose", "room.disconnect"]


async def test_room_is_left_even_when_the_runner_fails_to_close() -> None:
    calls: list[str] = []
    with pytest.raises(RuntimeError, match="runner stuck"):
        await worker(calls, RuntimeError("runner stuck")).aclose()
    assert calls == ["runner.aclose", "room.disconnect"]


class StartFakes:
    """Stand-ins for rtc.Room, DataStreamAudioReceiver and AvatarRunner inside start_avatar_worker."""

    def __init__(self, calls: list[str], runner_start: Any) -> None:
        self.calls = calls
        self.runner_start = runner_start

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls, runner_start = self.calls, self.runner_start

        class Room:
            async def connect(self, url: str, token: str, options: Any) -> None:
                calls.append("room.connect")

            async def disconnect(self) -> None:
                calls.append("room.disconnect")

        class Runner:
            def __init__(self, room: Any, **_: Any) -> None:
                pass

            async def start(self) -> None:
                calls.append("runner.start")
                await runner_start()

        monkeypatch.setattr(worker_module.rtc, "Room", Room)
        monkeypatch.setattr(worker_module, "DataStreamAudioReceiver", lambda room, **_: object())
        monkeypatch.setattr(worker_module, "AvatarRunner", Runner)


async def start(on_joined: Any = None) -> AvatarWorker:
    return await worker_module.start_avatar_worker(
        url="ws://livekit:7880", token="t", agent_identity="agent", options=OPTIONS, on_joined=on_joined
    )


async def test_on_joined_fires_once_the_room_is_joined_before_the_agent_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner waits for the agent; readiness must not (local cell healthcheck, NFR-O5)."""
    calls: list[str] = []

    async def agent_arrives() -> None:
        calls.append("agent arrived")

    StartFakes(calls, agent_arrives).install(monkeypatch)
    await start(on_joined=lambda: calls.append("joined"))
    assert calls == ["room.connect", "joined", "runner.start", "agent arrived"]


async def test_room_is_left_when_the_runner_fails_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fail() -> None:
        raise RuntimeError("runner broke")

    StartFakes(calls, fail).install(monkeypatch)
    with pytest.raises(RuntimeError, match="runner broke"):
        await start()
    assert calls[-1] == "room.disconnect"


async def test_room_is_left_when_start_is_cancelled_while_waiting_for_the_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    StartFakes(calls, asyncio.Event().wait).install(monkeypatch)
    task = asyncio.create_task(start())

    async def runner_started() -> None:
        while "runner.start" not in calls:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(runner_started(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls[-1] == "room.disconnect"
