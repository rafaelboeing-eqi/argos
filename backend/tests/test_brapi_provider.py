import httpx
import pytest

from app.services.market_data.brapi_provider import BrapiProvider
from app.services.market_data.exceptions import (
    BrapiAuthenticationError,
    BrapiInvalidResponseError,
    BrapiNotConfiguredError,
    BrapiPermissionError,
    BrapiTimeoutError,
)


def _provider(handler, token: str = "test-token") -> BrapiProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://brapi.dev")
    provider = BrapiProvider(client=client)
    provider._token = token
    return provider


def test_sends_bearer_authorization_header_and_no_token_in_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"asset": "DI1", "contracts": []})

    provider = _provider(handler, token="super-secret-token")
    provider.get_futures_term_structure("DI1")

    assert seen["authorization"] == "Bearer super-secret-token"
    assert "super-secret-token" not in seen["url"]


def test_missing_token_raises_not_configured_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not perform a request without a token")

    provider = _provider(handler, token="")
    with pytest.raises(BrapiNotConfiguredError):
        provider.get_futures_term_structure("DI1")


def test_401_raises_authentication_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": True, "message": "Token de autenticação inválido", "code": "INVALID_TOKEN"})

    provider = _provider(handler)
    with pytest.raises(BrapiAuthenticationError):
        provider.get_futures_term_structure("DI1")


def test_403_raises_permission_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": True, "message": "Acesso negado a este recurso", "code": "FORBIDDEN"})

    provider = _provider(handler)
    with pytest.raises(BrapiPermissionError):
        provider.get_futures_term_structure("DI1")


def test_timeout_raises_brapi_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider = _provider(handler)
    with pytest.raises(BrapiTimeoutError):
        provider.get_futures_term_structure("DI1")


def test_incomplete_payload_raises_invalid_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"asset": "DI1"})  # missing "contracts"

    provider = _provider(handler)
    with pytest.raises(BrapiInvalidResponseError):
        provider.get_futures_term_structure("DI1")


def test_macro_available_requires_results_key():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": []})

    provider = _provider(handler)
    with pytest.raises(BrapiInvalidResponseError):
        provider.get_macro_available()
