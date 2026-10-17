"""Short-lived, room-scoped LiveKit token for an avatar worker (LK-04, RT-06; SDD §7.3)."""

from __future__ import annotations

from datetime import timedelta

from livekit import api

PUBLISH_ON_BEHALF_ATTRIBUTE = "lk.publish_on_behalf"
MAX_TTL = timedelta(minutes=10)


def avatar_token(
    *,
    api_key: str,
    api_secret: str,
    room: str,
    avatar_identity: str,
    agent_identity: str,
    ttl: timedelta = MAX_TTL,
) -> str:
    """Mint a token for one room: the avatar joins as an agent publishing on behalf of `agent_identity`."""
    for name, value in (
        ("api_key", api_key),
        ("api_secret", api_secret),
        ("room", room),
        ("avatar_identity", avatar_identity),
        ("agent_identity", agent_identity),
    ):
        if not value:
            raise ValueError(f"{name} must not be empty")
    if avatar_identity == agent_identity:
        raise ValueError("avatar_identity and agent_identity must differ")
    if not timedelta(0) < ttl <= MAX_TTL:
        raise ValueError(f"ttl must be greater than 0 and at most {MAX_TTL}")

    grants = api.VideoGrants(
        room_join=True,
        room=room,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    return (
        api.AccessToken(api_key, api_secret)
        .with_identity(avatar_identity)
        .with_kind("agent")
        .with_attributes({PUBLISH_ON_BEHALF_ATTRIBUTE: agent_identity})
        .with_grants(grants)
        .with_ttl(ttl)
        .to_jwt()
    )
