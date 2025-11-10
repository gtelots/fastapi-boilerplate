# syntax=docker/dockerfile:1  # Enable Docker BuildKit features
# Keep this syntax directive! It's used to enable Docker BuildKit

########################################################
# BASE
# Sets up all our shared environment variables
########################################################
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS base

# Arguments
ARG TZ="UTC" \
    APP_PATH="/app" \
    UV_VERSION="0.9.7"

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    # Python
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Pip
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Uv
    VIRTUAL_ENV="/.venv" \
    UV_INSTALL_DIR="/opt/uv/bin" \
    UV_CACHE_DIR="/root/.cache/uv" \
    UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Ensure the installed binary is on the `PATH`
ENV PATH="$UV_INSTALL_DIR:$VIRTUAL_ENV/bin:$PATH"

# Add a non-root user to prevent files being created with root permissions on host machine.
ARG PU=laragis \
    PG=laragis \
    PUID=1000 \
    PGID=1000
ENV PUID=${PUID} \
    PGID=${PGID}

RUN \
    # Delete user & group if they exist
    getent passwd ${PUID} >/dev/null 2>&1 && userdel -r ${PU} || true &&\
    getent group ${PGID} >/dev/null 2>&1 && groupdel ${PG} || true &&\
    # Add group & user
    groupadd --force -g ${PGID} ${PG} &&\
    useradd -u ${PUID} -g ${PG} -s /bin/bash -m ${PU}

RUN \
    # Install system tools and libraries.
    --mount=type=cache,id=apt-base,target=/var/cache/apt \
    apt-get update &&\
    apt-get install -y --no-install-recommends curl ca-certificates &&\
    # Configure timezone
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone &&\
    # Install uv and create venv
    curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh &&\
    uv venv ${VIRTUAL_ENV} &&\
    # Cleanup apt update lists to keep the image size small
    apt-get autoremove --purge &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set the working directory inside the container
WORKDIR ${APP_PATH}

########################################################
# BUILDER
# Used to build deps + create our virtual environment
########################################################
FROM base AS builder

# Arguments
ARG TZ="UTC" \
    APP_PATH="/app"

# Metadata
ARG IMAGE_TITLE="FastAPI Boilerplate" \
    IMAGE_DESCRIPTION="A production-ready FastAPI boilerplate" \
    IMAGE_TAG="0.1.0" \
    IMAGE_SOURCE="https://github.com/gtelots/fastapi-boilerplate" \
    IMAGE_DOCUMENTATION="https://github.com/gtelots/fastapi-boilerplate/docs" \
    IMAGE_VENDOR="GTEL OTS" \
    IMAGE_AUTHORS="laragis <laragis.ots@gmail.com>" \
    IMAGE_LICENSES="MIT" \
    IMAGE_CREATED="2025-01-01T12:00:00Z"

LABEL org.opencontainers.image.title=${IMAGE_TITLE} \
      org.opencontainers.image.description=${IMAGE_DESCRIPTION} \
      org.opencontainers.image.version=${IMAGE_TAG} \
      org.opencontainers.image.source=${IMAGE_SOURCE} \
      org.opencontainers.image.documentation=${IMAGE_DOCUMENTATION} \
      org.opencontainers.image.vendor=${IMAGE_VENDOR} \
      org.opencontainers.image.authors=${IMAGE_AUTHORS} \
      org.opencontainers.image.licenses=${IMAGE_LICENSES} \
      org.opencontainers.image.created=${IMAGE_CREATED}

# Copy lock files
COPY uv.lock pyproject.toml ./

# Install dependencies with uv, caching downloaded packages
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --active --locked --no-install-project

########################################################
# RUNNER
########################################################
FROM builder AS runner

# Arguments
ARG APP_PORT=8000
ENV APP_PORT=${APP_PORT}

# Copy in our built venv
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy the application code to the working directory
COPY . .

# Copying in our entrypoint
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the port the app runs on
EXPOSE ${APP_PORT}

########################################################
# DEVELOPMENT
# Image used during development / testing
########################################################
FROM runner AS development

# Install system tools and libraries.
RUN --mount=type=cache,id=apt-build,target=/var/cache/apt \
    apt-get update &&\
    apt-get install -y --no-install-recommends tmux zsh &&\
    apt-get autoremove --purge &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Sync the project with all groups
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --active --locked --no-install-project --all-groups

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]

# Start server
CMD ["sh", "-c", "uvicorn app.app:app --host 0.0.0.0 --port ${APP_PORT} --reload"]

########################################################
# PRODUCTION
# Final image used for runtime
########################################################
FROM runner AS production

# Sync the project with no dev deps
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --active --locked --no-editable --no-dev

# Add a non-root user to prevent files being created with root permissions on host machine.
ENV PUID=1000 \
    PGID=1000

# Switch to user
RUN chown -R ${PUID}:${PGID} ./
USER ${PUID}:${PGID}

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]

# Start server
CMD ["sh", "-c", "uvicorn app.app:app --host 0.0.0.0 --port ${APP_PORT}"]
