FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
COPY packages ./packages
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services

ENV PYTHONPATH=/app/packages/shared/src
