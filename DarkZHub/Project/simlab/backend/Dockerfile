FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Optional pip mirror for restricted networks:
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=""
RUN pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url ${PIP_INDEX_URL}} -r requirements.txt

COPY . .

EXPOSE 8003
