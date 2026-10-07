# HRB Leave Management MCP server, as a container image.
#
# Build it from the REPOSITORY ROOT, not from anywhere else:
#
#     docker build -t hrb-lms-mcp:local .
#
# Two stages - the builder installs dependencies, the runtime stage copies
# the finished virtual environment across and nothing else. Mirrors
# hrb_chatbot_v2's own Dockerfile pattern (sibling project, same account),
# much lighter here - no spaCy/Presidio model download, just FastMCP +
# SQLAlchemy/psycopg2 + PyJWT.

# ---------------------------------------------------------------------------
# Stage 1 - build the virtual environment
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY requirements.txt ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 - the image that actually runs
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    SERVER_PORT=8190

# curl is for the HEALTHCHECK below - psycopg2-binary needs no extra
# runtime libs (unlike the source psycopg2 package).
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Run as a normal user, same reasoning as hrb_chatbot_v2's own Dockerfile -
# nothing here needs root.
RUN useradd --create-home --uid 10001 lmsmcp

COPY --from=builder /opt/venv /opt/venv

# /srv holds src/ so imports written as `from src.app...` resolve the same
# way they do when running locally from the repository root.
WORKDIR /srv
COPY --chown=lmsmcp:lmsmcp src ./src

USER lmsmcp

EXPOSE 8190

# /hrb_emp_lms/health/app only confirms the process is up - no database
# call, matching hrb_chatbot_v2's own /ping-vs-/health split (its own
# RAG-ROADMAP.md documents why a container probe must never depend on a
# backend being up).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8190/hrb_emp_lms/health/app || exit 1

CMD ["uvicorn", "src.app.api.main:app", "--host", "0.0.0.0", "--port", "8190"]
