"""Provisionamento idempotente do bucket público 'avatars' (007)."""

from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command


def _run(buckets):
    storage = mock.MagicMock()
    storage.list_buckets.return_value = buckets
    with mock.patch("apps.accounts.avatars._storage", return_value=storage):
        call_command("provision_avatars_bucket", stdout=StringIO())
    return storage


def test_creates_public_bucket_when_missing():
    storage = _run(buckets=[])

    storage.create_bucket.assert_called_once_with("avatars", options={"public": True})


def test_is_noop_when_public_bucket_exists():
    storage = _run(buckets=[SimpleNamespace(id="avatars", public=True)])

    storage.create_bucket.assert_not_called()
    storage.update_bucket.assert_not_called()


def test_makes_existing_private_bucket_public():
    storage = _run(buckets=[SimpleNamespace(id="avatars", public=False)])

    storage.update_bucket.assert_called_once_with("avatars", options={"public": True})
