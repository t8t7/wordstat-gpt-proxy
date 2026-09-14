FROM python:3.12.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        chromium \
        chromium-driver \
        novnc \
        websockify \
        x11vnc \
        xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --no-create-home app \
    && mkdir -p /var/lib/wordstat-browser \
    && chown app:app /var/lib/wordstat-browser

COPY requirements.txt ./
RUN pip install --requirement requirements.txt

COPY app ./app
COPY docker/entrypoint.sh /usr/local/bin/wordstat-entrypoint
RUN chmod 0755 /usr/local/bin/wordstat-entrypoint

USER app
EXPOSE 8000

CMD ["/usr/local/bin/wordstat-entrypoint"]
