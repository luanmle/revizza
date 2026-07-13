import pytest


@pytest.mark.django_db
def test_accept_header_supports_current_and_previous_contract(
    auth_client, make_deck
):
    make_deck()

    current = auth_client.get(
        "/api/v1/decks/", HTTP_ACCEPT="application/json; version=1"
    )
    previous = auth_client.get(
        "/api/v1/decks/", HTTP_ACCEPT="application/json; version=0"
    )

    assert current.status_code == 200
    assert "Deprecation" not in current
    assert previous.status_code == 200
    assert previous["Deprecation"] == "true"
    assert "API version 0 is deprecated" in previous["Warning"]
    assert "Accept" in previous["Vary"]


@pytest.mark.django_db
def test_accept_header_rejects_unsupported_contract(auth_client):
    response = auth_client.get(
        "/api/v1/decks/", HTTP_ACCEPT="application/json; version=99"
    )

    assert response.status_code == 406

