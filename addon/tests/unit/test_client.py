from ankihub_br.ankihub_br_client import AnkiHubBrClient


def test_client_rejects_non_https_base_url():
    try:
        AnkiHubBrClient("http://api.example.com")
    except ValueError as exc:
        assert str(exc) == "A URL da API deve usar HTTPS."
    else:
        raise AssertionError("HTTP API URL was accepted")
