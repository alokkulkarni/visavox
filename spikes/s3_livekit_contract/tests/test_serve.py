"""Stand-in avatar entry point for the local cell (NFR-O5, RT-06, LK-04; SDD §14)."""

from __future__ import annotations

import asyncio
import base64
import json
import signal
from pathlib import Path
from typing import Any

import pytest

from s3_livekit_contract import serve as serve_module
from s3_livekit_contract.serve import ServeConfig, main, serve

SECRET = "test-secret-0123456789-abcdefghijklmnop"


def env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    values = {
        "LIVEKIT_URL": "ws://livekit:7880",
        "LIVEKIT_API_KEY": "testkey",
        "LIVEKIT_API_SECRET": SECRET,
        "AVATAR_ROOM": "local-demo",
        "AGENT_IDENTITY": "local-agent",
        "READY_FILE": str(tmp_path / "ready"),
    }
    values.update(overrides)
    return values


def claims(token: str) -> dict[str, Any]:
    segment = token.split(".")[1]
    data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
    return data


class FakeWorker:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeStart:
    """Joins (calls on_joined), then waits for `agent_arrives` before returning, like AvatarRunner."""

    def __init__(self, agent_arrives: asyncio.Event | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.worker = FakeWorker()
        self.agent_arrives = agent_arrives
        self.error = error

    async def __call__(self, **kwargs: Any) -> FakeWorker:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        kwargs["on_joined"]()
        if self.agent_arrives is not None:
            await self.agent_arrives.wait()
        return self.worker


class TestConfig:
    def test_reads_every_setting_from_the_environment(self, tmp_path: Path) -> None:
        config = ServeConfig.from_env(env(tmp_path, AVATAR_IDENTITY="avatar-x"))
        assert config.url == "ws://livekit:7880"
        assert config.room == "local-demo"
        assert config.agent_identity == "local-agent"
        assert config.avatar_identity == "avatar-x"
        assert config.ready_file == tmp_path / "ready"

    def test_avatar_identity_has_a_default(self, tmp_path: Path) -> None:
        assert ServeConfig.from_env(env(tmp_path)).avatar_identity == "local-avatar"

    @pytest.mark.parametrize(
        "name", ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "AVATAR_ROOM", "AGENT_IDENTITY"]
    )
    def test_missing_required_setting_names_the_variable(self, tmp_path: Path, name: str) -> None:
        values = env(tmp_path)
        del values[name]
        with pytest.raises(ValueError, match=name):
            ServeConfig.from_env(values)

    def test_secret_is_hidden_from_repr(self, tmp_path: Path) -> None:
        assert SECRET not in repr(ServeConfig.from_env(env(tmp_path)))


class TestServe:
    async def test_joins_with_a_room_scoped_avatar_token_and_reports_ready(self, tmp_path: Path) -> None:
        config = ServeConfig.from_env(env(tmp_path))
        start, stop = FakeStart(), asyncio.Event()
        task = asyncio.create_task(serve(config, stop, start=start))
        await asyncio.wait_for(_until(lambda: config.ready_file.exists()), timeout=2)

        (call,) = start.calls
        assert call["url"] == "ws://livekit:7880"
        assert call["agent_identity"] == "local-agent"
        token = claims(call["token"])
        assert token["sub"] == "local-avatar"
        assert token["video"]["room"] == "local-demo"
        assert token["kind"] == "agent"

        stop.set()
        await asyncio.wait_for(task, timeout=2)
        assert start.worker.closed
        assert not config.ready_file.exists()

    async def test_worker_is_closed_even_if_serving_is_cancelled(self, tmp_path: Path) -> None:
        config = ServeConfig.from_env(env(tmp_path))
        start = FakeStart()
        task = asyncio.create_task(serve(config, asyncio.Event(), start=start))
        await asyncio.wait_for(_until(lambda: config.ready_file.exists()), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert start.worker.closed
        assert not config.ready_file.exists()

    async def test_is_ready_and_stoppable_before_any_agent_arrives(self, tmp_path: Path) -> None:
        """The healthcheck must pass while the avatar waits for its agent (NFR-O5)."""
        config = ServeConfig.from_env(env(tmp_path))
        start, stop = FakeStart(agent_arrives=asyncio.Event()), asyncio.Event()
        task = asyncio.create_task(serve(config, stop, start=start))
        await asyncio.wait_for(_until(lambda: config.ready_file.exists()), timeout=2)
        stop.set()
        await asyncio.wait_for(task, timeout=2)
        assert not config.ready_file.exists()
        assert not start.worker.closed  # never handed over: start was cancelled, which leaves the room itself

    async def test_failure_to_start_ends_serving_with_the_error(self, tmp_path: Path) -> None:
        """A crash must exit the process so Docker restarts it, not leave an idle unhealthy container."""
        config = ServeConfig.from_env(env(tmp_path))
        start = FakeStart(error=ConnectionError("livekit unreachable"))
        with pytest.raises(ConnectionError, match="livekit unreachable"):
            await asyncio.wait_for(serve(config, asyncio.Event(), start=start), timeout=2)
        assert not config.ready_file.exists()


def test_main_serves_until_a_termination_signal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in env(tmp_path).items():
        monkeypatch.setenv(key, value)
    seen: dict[str, Any] = {}

    async def fake_serve(config: ServeConfig, stop: asyncio.Event, **_: Any) -> None:
        seen["room"] = config.room
        signal.raise_signal(signal.SIGTERM)
        await asyncio.wait_for(stop.wait(), timeout=2)
        seen["stopped"] = True

    monkeypatch.setattr(serve_module, "serve", fake_serve)
    main()
    assert seen == {"room": "local-demo", "stopped": True}


async def _until(predicate: Any) -> None:
    while not predicate():
        await asyncio.sleep(0.01)
