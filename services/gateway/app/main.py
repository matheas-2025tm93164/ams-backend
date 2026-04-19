from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

_settings = get_settings()
_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _client
    _client = httpx.AsyncClient(timeout=120.0)
    yield
    if _client:
        await _client.aclose()
    _client = None


app = FastAPI(title="API Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _filter_request_headers(headers: httpx.Headers) -> dict[str, str]:
    skip = {"host", "connection", "content-length"}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


def _filter_response_headers(h: httpx.Headers) -> dict[str, str]:
    skip = {"connection", "transfer-encoding", "content-encoding", "keep-alive"}
    out: dict[str, str] = {}
    for k, v in h.items():
        if k.lower() in skip:
            continue
        out[k] = v
    return out


async def _proxy(base: str, request: Request) -> Response:
    if _client is None:
        raise RuntimeError("client not ready")
    path = request.url.path
    query = str(request.query_params) if request.query_params else ""
    url = f"{base.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    body = await request.body()
    hdrs = _filter_request_headers(request.headers)
    r = await _client.request(
        request.method,
        url,
        content=body if body else None,
        headers=hdrs,
    )
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers=_filter_response_headers(r.headers),
        media_type=r.headers.get("content-type"),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.api_route("/auth/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_auth(full_path: str, request: Request) -> Response:
    return await _proxy(_settings.user_service_url, request)


@app.api_route("/auth", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_auth_root(request: Request) -> Response:
    return await _proxy(_settings.user_service_url, request)


@app.api_route("/complaints/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_complaints(full_path: str, request: Request) -> Response:
    return await _proxy(_settings.complaint_service_url, request)


@app.api_route("/complaints", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_complaints_root(request: Request) -> Response:
    return await _proxy(_settings.complaint_service_url, request)


@app.api_route("/analytics/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_analytics(full_path: str, request: Request) -> Response:
    return await _proxy(_settings.complaint_service_url, request)


@app.api_route("/analytics", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_analytics_root(request: Request) -> Response:
    return await _proxy(_settings.complaint_service_url, request)
