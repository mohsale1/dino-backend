# ── Stage 1: build wheels ────────────────────────────────────────────────────
# Use the full slim image to compile any C/Rust extensions (bcrypt, asyncpg,
# pydantic-core) into pre-built wheels. The compiled artefacts are then copied
# into the lean runtime stage — no compiler toolchain ends up in the final image.
FROM python:3.11-slim AS builder

WORKDIR /wheels

# Install build tools only in this stage; they are NOT carried into the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build all wheels into /wheels. pip will reuse pre-built manylinux wheels from
# PyPI where available (bcrypt, asyncpg, pydantic-core all ship them), so gcc
# is only invoked for packages that genuinely need compilation.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Deployment identity — injected at build time via --build-arg.
# Baked into the image so every startup log shows exactly which build is running.
ARG BUILD_ID=local
ARG DEPLOYED_AT=unknown
ENV BUILD_ID=${BUILD_ID} \
    DEPLOYED_AT=${DEPLOYED_AT} \
    # Prevent .pyc files from being written into the image layer
    PYTHONDONTWRITEBYTECODE=1 \
    # Force stdout/stderr to be unbuffered so logs appear immediately
    PYTHONUNBUFFERED=1 \
    # Tell pip not to check for upgrades and skip the cache
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install pre-built wheels from the builder stage — no compiler needed here.
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Create a non-root user before copying application code.
RUN useradd -m -u 1000 appuser

# Copy application source.
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uvicorn src.Main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2"]
