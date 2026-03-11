import pytest
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from tests.asgi_testclient import ASGITestClient


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def test_asgi_testclient_defaults_to_localhost():
    client = ASGITestClient(_build_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_asgi_testclient_works_inside_async_tests():
    client = ASGITestClient(_build_app())

    response = client.get("/health")

    assert response.status_code == 200
