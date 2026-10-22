# CPU stand-in avatar for the local cell (NFR-O5, SDD §14). Serves the LiveKit avatar contract with the
# synthetic generator from spike S3; LK1 replaces it with services/avatar-engine. Build context: repo root.
FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv

FROM python:3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
WORKDIR /src
COPY . .
RUN uv sync --frozen --no-dev --package s3-livekit-contract && rm -rf /root/.cache
RUN useradd --system --uid 10001 avatar
USER avatar
CMD ["python", "-m", "s3_livekit_contract.serve"]
