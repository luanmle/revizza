"""Única camada do add-on que fala HTTP com o backend (plan.md Project Structure).

Auth via Bearer token do Supabase, retry/backoff automático em 429/5xx (respeita
Retry-After — FR-032) e versionamento de contrato via header Accept.
"""

from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_VERSION = "1"
DEFAULT_TIMEOUT = 30  # segundos


class AnkiHubBrClient:
    def __init__(
        self,
        api_base_url: str,
        token: str | None = None,
        anki_version: str | None = None,
        sync_run_id: str | None = None,
    ):
        parsed_url = urlsplit(api_base_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("A URL da API deve usar HTTPS.")
        self.api_base_url = api_base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["Accept"] = f"application/json; version={API_VERSION}"
        if anki_version:
            # telemetria/diagnóstico da política LTS (FR-038, contracts/sync.md)
            self.session.headers["X-Anki-Version"] = anki_version
        if sync_run_id:
            self.session.headers["X-Sync-Run-ID"] = sync_run_id

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        response = self.session.request(method, f"{self.api_base_url}{path}", **kwargs)
        response.raise_for_status()
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("DELETE", path, **kwargs)

    # --- API de sincronização (contracts/sync.md, contracts/catalog.md) ---

    def get_subscribed_decks(self) -> list[dict]:
        return self.get("/decks/", params={"subscribed": "1"}).json()["results"]

    def test_connection(self) -> dict[str, bool | None]:
        try:
            self.get("/health/")
        except requests.RequestException:
            return {"api_ok": False, "session_ok": None}
        if not self.token:
            return {"api_ok": True, "session_ok": None}
        try:
            self.get("/accounts/me/")
        except requests.RequestException:
            return {"api_ok": True, "session_ok": False}
        return {"api_ok": True, "session_ok": True}

    def update_subscription_preferences(self, deck_id: str, preferences: dict) -> dict:
        return self.patch(
            f"/decks/{deck_id}/subscriptions/me/", json=preferences
        ).json()

    def unsubscribe(self, deck_id: str) -> None:
        self.delete(f"/decks/{deck_id}/subscriptions/me/")

    def get_deck_delta(self, deck_id: str, since_mod: str | None = None) -> dict:
        params = {"since_mod": since_mod} if since_mod else None
        return self.get(f"/decks/{deck_id}/sync/delta/", params=params).json()

    def get_deck_full(self, deck_id: str) -> dict:
        return self.get(f"/decks/{deck_id}/sync/full/").json()

    def get_deck_protection(self, deck_id: str) -> dict:
        return self.get(f"/decks/{deck_id}/protection/me/").json()

    def resolve_note(self, guid: str) -> dict:
        """GUID → {note_id, deck_id, web_url, history_url} (US2, auth)."""
        return self.get("/notes/resolve/", params={"guid": guid}).json()

    def submit_change_suggestion(
        self,
        note_id: str,
        fields: dict,
        tags: list[str],
        category: str,
        justification: str,
    ) -> dict:
        """Envia sugestão de mudança pelo pipeline existente (US2)."""
        return self.post(
            f"/notes/{note_id}/suggestions/change/",
            json={
                "change_category": category,
                "justification": justification,
                "proposed_field_values": fields,
                "tags": tags,
            },
        ).json()

    def get_media_url(self, content_hash: str) -> str:
        return self.get(f"/media/{content_hash}/").json()["url"]

    def download_file(self, url: str) -> bytes:
        # URL pré-assinada do Storage — sem o header Authorization da API
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.content

    def publish_deck(self, deck_id: str, payload: dict) -> dict:
        return self.post(f"/decks/{deck_id}/publish/", json=payload).json()

    def upload_signed_media(self, url: str, filename: str, content: bytes) -> None:
        # Supabase signed upload: multipart PUT; não vaza o Bearer da API.
        response = requests.put(
            url,
            files={"file": (filename, content, "application/octet-stream")},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
