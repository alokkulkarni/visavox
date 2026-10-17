"""Avatar worker tokens: short-lived, one room, kind=agent, publishing on behalf of the agent (LK-04, RT-06)."""

from __future__ import annotations

import base64
import json
from datetime import timedelta
from typing import Any

import pytest
from livekit import api

from s3_livekit_contract.tokens import MAX_TTL, PUBLISH_ON_BEHALF_ATTRIBUTE, avatar_token

KEY = "testkey"
SECRET = "test-secret-0123456789-abcdefghijklmnop"


def make(**overrides: Any) -> str:
    args: dict[str, Any] = {
        "api_key": KEY,
        "api_secret": SECRET,
        "room": "room-a",
        "avatar_identity": "avatar-1",
        "agent_identity": "agent-1",
    }
    args.update(overrides)
    return avatar_token(**args)


def payload(token: str) -> dict[str, Any]:
    segment = token.split(".")[1]
    segment += "=" * (-len(segment) % 4)
    data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(segment))
    return data


def test_token_identifies_avatar_as_agent_publishing_on_behalf_of_the_agent() -> None:
    claims = api.TokenVerifier(KEY, SECRET).verify(make())
    assert claims.identity == "avatar-1"
    assert claims.kind == "agent"
    assert claims.attributes == {PUBLISH_ON_BEHALF_ATTRIBUTE: "agent-1"}


def test_token_is_scoped_to_one_room_without_admin_rights() -> None:
    video = api.TokenVerifier(KEY, SECRET).verify(make()).video
    assert video is not None
    assert video.room_join is True
    assert video.room == "room-a"
    assert not video.room_admin
    assert not video.room_create
    assert not video.room_list
    assert not video.room_record
    assert video.can_publish is True
    assert video.can_publish_data is True


def test_default_lifetime_is_the_maximum_of_ten_minutes() -> None:
    claims = payload(make())
    assert MAX_TTL == timedelta(minutes=10)
    assert claims["exp"] - claims["nbf"] == 600


def test_shorter_lifetime_is_respected() -> None:
    claims = payload(make(ttl=timedelta(minutes=2)))
    assert claims["exp"] - claims["nbf"] == 120


@pytest.mark.parametrize("ttl", [timedelta(0), timedelta(seconds=-1), timedelta(minutes=11)])
def test_lifetime_outside_bounds_is_rejected(ttl: timedelta) -> None:
    with pytest.raises(ValueError, match="ttl"):
        make(ttl=ttl)


@pytest.mark.parametrize("field", ["room", "avatar_identity", "agent_identity", "api_key", "api_secret"])
def test_empty_fields_are_rejected(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        make(**{field: ""})


def test_avatar_cannot_publish_on_behalf_of_itself() -> None:
    with pytest.raises(ValueError, match="differ"):
        make(agent_identity="avatar-1")
