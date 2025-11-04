ARG PYTHON_VERSION=3.11-slim

FROM python:${PYTHON_VERSION}

ARG SERVICE_DIR
ENV SERVICE_DIR=${SERVICE_DIR}

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

COPY ${SERVICE_DIR}/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY common /app/common
COPY ${SERVICE_DIR}/app /app/app

ENV PYTHONPATH=/app

CMD ["python", "-m", "app"]

