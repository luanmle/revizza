"""Contract test: POST /api/v1/accounts/register/ (contracts/accounts.md, FR-001/004/005)."""

import uuid

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/accounts/register/"


@pytest.fixture
def mock_sign_up(monkeypatch):
    auth_id = str(uuid.uuid4())
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.sign_up", lambda email, password: auth_id
    )
    return auth_id


def test_register_creates_profile_with_consents_off_by_default(
    api_client, mock_sign_up
):
    response = api_client.post(
        URL, {"email": "novo@example.com", "password": "s3nha-forte"}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "novo@example.com"
    # FR-005: consentimentos nunca pré-marcados
    assert body["consent_marketing_emails"] is False
    assert body["consent_research_data"] is False
    # FR-001: senha nunca armazenada/exposta
    assert "password" not in body
    user = User.objects.get(email="novo@example.com")
    assert str(user.auth_id) == mock_sign_up


def test_register_accepts_optional_career_board_and_consents(api_client, mock_sign_up):
    response = api_client.post(
        URL,
        {
            "name": "Ana Souza",
            "email": "novo@example.com",
            "password": "s3nha-forte",
            "target_career": "fiscal",
            "target_board": "CEBRASPE",
            "consent_marketing_emails": True,
            "consent_research_data": True,
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="novo@example.com")
    assert user.name == "Ana Souza"
    assert user.target_career == "fiscal"
    assert user.target_board == "CEBRASPE"
    assert user.consent_marketing_emails is True
    assert user.consent_research_data is True


def test_register_rejects_invalid_payload(api_client, mock_sign_up):
    response = api_client.post(
        URL, {"email": "nao-e-email", "password": "curta"}, format="json"
    )

    assert response.status_code == 400
    assert not User.objects.exists()


def test_register_maps_supabase_failure_to_400(api_client, monkeypatch):
    def boom(email, password):
        raise RuntimeError("User already registered")

    monkeypatch.setattr("apps.accounts.supabase_gateway.sign_up", boom)

    response = api_client.post(
        URL, {"email": "novo@example.com", "password": "s3nha-forte"}, format="json"
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    assert not User.objects.exists()


def test_password_reset_returns_204_without_leaking_existence(api_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.send_password_reset", calls.append
    )

    response = api_client.post(
        "/api/v1/accounts/password-reset/",
        {"email": "quem@example.com"},
        format="json",
    )

    assert response.status_code == 204
    assert calls == ["quem@example.com"]
