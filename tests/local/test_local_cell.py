"""Smoke tests for the local Docker cell: every dependency answers as the cloud cell would (NFR-O5).

Run with `make up` then `make test-local`. Data is synthetic; nothing leaves the machine.
"""

from __future__ import annotations

import asyncio
import json
import math
import socket
import time
import urllib.request
import uuid
from typing import Any

import asyncpg
import boto3
import numpy as np
import pytest
from livekit import api, rtc
from livekit.agents.voice.avatar import DataStreamAudioOutput

from .conftest import (
    AGENT_IDENTITY,
    AVATAR_IDENTITY,
    AVATAR_ROOM,
    AWS_ENDPOINT_URL,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_HTTP_URL,
    LIVEKIT_URL,
    OIDC_ISSUER,
    POSTGRES_DSN,
    VALKEY_HOST,
    VALKEY_PORT,
)

pytestmark = pytest.mark.local

SAMPLE_RATE = 24_000


async def test_livekit_room_api_answers() -> None:
    async with api.LiveKitAPI(LIVEKIT_HTTP_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) as lk:
        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
    assert rooms is not None


async def test_postgres_app_role_cannot_bypass_row_level_security() -> None:
    """ADR-004: services connect as a non-owner role that cannot bypass RLS."""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        row = await conn.fetchrow(
            "SELECT current_database() AS db, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
            "FROM pg_roles WHERE rolname = current_user"
        )
        owner = await conn.fetchval(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'visavox'"
        )
    finally:
        await conn.close()
    assert row is not None
    assert row["db"] == "visavox"
    assert not row["rolsuper"]
    assert not row["rolbypassrls"]
    assert not row["rolcreaterole"]
    assert not row["rolcreatedb"]
    assert owner == "visavox_owner"


def test_valkey_answers_ping() -> None:
    with socket.create_connection((VALKEY_HOST, VALKEY_PORT), timeout=5) as conn:
        conn.sendall(b"PING\r\n")
        assert conn.recv(64) == b"+PONG\r\n"


def emulator(service: str) -> Any:
    """A boto3 client for the local AWS emulator; it accepts any credentials, so these are not real ones."""
    return boto3.client(
        service,
        endpoint_url=AWS_ENDPOINT_URL,
        region_name="eu-west-2",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )


def test_s3_stand_in_stores_objects() -> None:
    s3, bucket = emulator("s3"), f"visavox-local-{uuid.uuid4().hex[:8]}"
    s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
    s3.put_object(Bucket=bucket, Key="synthetic.txt", Body=b"synthetic")
    assert s3.get_object(Bucket=bucket, Key="synthetic.txt")["Body"].read() == b"synthetic"


def test_sqs_stand_in_delivers_messages() -> None:
    sqs = emulator("sqs")
    url = sqs.create_queue(QueueName=f"visavox-local-{uuid.uuid4().hex[:8]}")["QueueUrl"]
    sqs.send_message(QueueUrl=url, MessageBody="synthetic")
    messages = sqs.receive_message(QueueUrl=url, WaitTimeSeconds=1)["Messages"]
    assert [m["Body"] for m in messages] == ["synthetic"]


def test_kms_stand_in_encrypts_and_decrypts() -> None:
    kms = emulator("kms")
    key = kms.create_key(Description="local synthetic key")["KeyMetadata"]["KeyId"]
    blob = kms.encrypt(KeyId=key, Plaintext=b"synthetic")["CiphertextBlob"]
    assert blob != b"synthetic"
    assert kms.decrypt(CiphertextBlob=blob)["Plaintext"] == b"synthetic"


def test_secrets_manager_stand_in_round_trips_a_synthetic_value() -> None:
    sm, name = emulator("secretsmanager"), f"visavox/local/{uuid.uuid4().hex[:8]}"
    sm.create_secret(Name=name, SecretString="synthetic")
    assert sm.get_secret_value(SecretId=name)["SecretString"] == "synthetic"


def test_oidc_stand_in_publishes_discovery_and_keys() -> None:
    discovery_url = f"{OIDC_ISSUER}/.well-known/openid-configuration"
    with urllib.request.urlopen(discovery_url, timeout=5) as resp:  # noqa: S310
        discovery = json.load(resp)
    assert discovery["issuer"] == OIDC_ISSUER
    with urllib.request.urlopen(discovery["jwks_uri"], timeout=5) as resp:  # noqa: S310
        assert json.load(resp)["keys"]


async def _connect(identity: str, kind: str = "standard") -> rtc.Room:
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_kind(kind)  # type: ignore[arg-type]
        .with_grants(api.VideoGrants(room_join=True, room=AVATAR_ROOM))
        .to_jwt()
    )
    room = rtc.Room()
    await room.connect(LIVEKIT_URL, token)
    return room


async def _speak_one_second() -> tuple[float, bool, int]:
    """One agent turn against the containerised stand-in avatar; returns (position, interrupted, frames)."""
    agent = await _connect(AGENT_IDENTITY, kind="agent")
    viewer = await _connect(f"viewer-{uuid.uuid4().hex[:8]}")
    frames: list[float] = []

    async def watch() -> None:
        deadline = time.monotonic() + 15
        track: rtc.Track | None = None
        while track is None:
            if time.monotonic() > deadline:
                raise TimeoutError("stand-in avatar video track not found")
            avatar = viewer.remote_participants.get(AVATAR_IDENTITY)
            pubs = avatar.track_publications.values() if avatar else []
            track = next((p.track for p in pubs if p.kind == rtc.TrackKind.KIND_VIDEO and p.track), None)
            await asyncio.sleep(0.1)
        async for _ in rtc.VideoStream(track):
            frames.append(time.monotonic())

    watcher = asyncio.create_task(watch())
    try:
        out = DataStreamAudioOutput(
            agent,
            destination_identity=AVATAR_IDENTITY,
            sample_rate=SAMPLE_RATE,
            wait_remote_track=rtc.TrackKind.KIND_VIDEO,
            wait_playback_start=True,
        )
        t = np.arange(SAMPLE_RATE) / SAMPLE_RATE
        samples = (np.sin(2 * math.pi * 440 * t) * 8_000).astype(np.int16)
        for chunk in np.split(samples, range(SAMPLE_RATE // 10, SAMPLE_RATE, SAMPLE_RATE // 10)):
            await out.capture_frame(rtc.AudioFrame(chunk.tobytes(), SAMPLE_RATE, 1, len(chunk)))
        out.flush()
        event = await asyncio.wait_for(out.wait_for_playout(), timeout=20)
        await asyncio.sleep(0.5)
        return event.playback_position, event.interrupted, len(frames)
    finally:
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)
        await asyncio.wait_for(agent.disconnect(), timeout=10)
        await asyncio.wait_for(viewer.disconnect(), timeout=10)


async def test_stand_in_avatar_speaks_and_streams_video_across_agent_reconnects() -> None:
    """RT-02, RT-06: the containerised avatar serves an agent turn, then serves a reconnecting agent."""
    for _turn in range(2):
        position, interrupted, frames = await _speak_one_second()
        assert position == pytest.approx(1.0, abs=0.15)
        assert interrupted is False
        assert frames >= 20
