ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.12-alpine3.23
FROM ${BUILD_FROM}

ARG CACTUS_VERSION=4.2.5
ENV PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONUNBUFFERED=1 \
    CACTUS_TELEMETRY=0 \
    HF_HOME=/data/huggingface \
    XDG_CACHE_HOME=/data/cache

RUN pip3 install --no-cache-dir "cactus-compute==${CACTUS_VERSION}"

COPY cactus_needle/server.py /opt/cactus-needle/server.py
COPY cactus_needle/rootfs /
RUN chmod a+x /etc/services.d/cactus-needle/run

HEALTHCHECK --start-period=5m --interval=30s --timeout=10s --retries=3 \
  CMD python3 -c "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=5))['status']=='ok'" || exit 1

