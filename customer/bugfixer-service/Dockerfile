FROM python:3.12-slim

ARG GH_VERSION=2.60.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates nodejs npm make build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL \
        "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" \
        | tar -xz -C /tmp \
    && mv "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh_*

# OpenCode CLI. Verify the installed version's flags with: opencode run --help
RUN npm install -g opencode-ai

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN mkdir -p /work /app/media \
    && useradd --create-home --uid 10001 --shell /bin/sh bugfixer \
    && chown -R bugfixer:bugfixer /work /app/media

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
