def test_health_is_public_and_database_free(api_client):
    response = api_client.get(
        "/api/v1/health/", HTTP_AUTHORIZATION="Bearer expired-token"
    )

    assert response.status_code == 200
