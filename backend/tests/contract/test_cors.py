"""T129: CORS para a topologia frontend/backend separados (FR-002)."""

import pytest

pytestmark = pytest.mark.django_db

CATALOG_URL = "/api/v1/decks/"
ALLOWED_ORIGIN = "http://localhost:3000"


def test_preflight_allows_configured_frontend_origin(api_client):
    response = api_client.options(
        CATALOG_URL,
        HTTP_ORIGIN=ALLOWED_ORIGIN,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
    )

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert "authorization" in response["Access-Control-Allow-Headers"].lower()


def test_preflight_rejects_unknown_origin(api_client):
    response = api_client.options(
        CATALOG_URL,
        HTTP_ORIGIN="https://malicioso.example.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )

    assert "Access-Control-Allow-Origin" not in response


def test_authenticated_request_carries_cors_header(auth_client):
    response = auth_client.get(CATALOG_URL, HTTP_ORIGIN=ALLOWED_ORIGIN)

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
