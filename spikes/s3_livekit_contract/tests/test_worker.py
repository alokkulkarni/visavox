"""AvatarWorker shutdown always releases its room (RT-06, LK-01; S3 finding 4, issue #9)."""

from __future__ import annotations

from typing import Any, cast

import pytest

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
