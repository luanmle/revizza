"""T137: provisionamento idempotente do bucket privado 'media' (FR-036)."""

from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command


def _run(buckets):
    storage = mock.MagicMock()
    storage.list_buckets.return_value = buckets
    with mock.patch("apps.sync.media._storage", return_value=storage):
        call_command("provision_media_bucket", stdout=StringIO())
    return storage


def test_creates_private_bucket_when_missing():
    storage = _run(buckets=[])

    storage.create_bucket.assert_called_once_with("media", options={"public": False})


def test_is_noop_when_private_bucket_exists():
    storage = _run(buckets=[SimpleNamespace(id="media", public=False)])

    storage.create_bucket.assert_not_called()
    storage.update_bucket.assert_not_called()


def test_makes_existing_public_bucket_private():
    storage = _run(buckets=[SimpleNamespace(id="media", public=True)])

    storage.update_bucket.assert_called_once_with("media", options={"public": False})
