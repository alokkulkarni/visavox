"""Endpoints of the running local cell (`make up`; NFR-O5, SDD §14).

Defaults match deploy/local/compose.yaml. Every value is local-only and synthetic; override with
the environment variables named below when running against a different local cell.
"""

from __future__ import annotations

import os

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_HTTP_URL = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "secret")

POSTGRES_DSN = os.environ.get(
    "LOCAL_POSTGRES_DSN", "postgresql://visavox_app:local-only@localhost:55432/visavox"
)
VALKEY_HOST, VALKEY_PORT = "localhost", int(os.environ.get("LOCAL_VALKEY_PORT", "56379"))
AWS_ENDPOINT_URL = os.environ.get("LOCAL_AWS_ENDPOINT_URL", "http://localhost:55000")
OIDC_ISSUER = os.environ.get("LOCAL_OIDC_ISSUER", "http://localhost:58080/visavox")

AVATAR_ROOM = os.environ.get("AVATAR_ROOM", "local-demo")
AGENT_IDENTITY = os.environ.get("AGENT_IDENTITY", "local-agent")
AVATAR_IDENTITY = os.environ.get("AVATAR_IDENTITY", "local-avatar")
