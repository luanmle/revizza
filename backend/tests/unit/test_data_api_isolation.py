"""T127: checagem de deploy do isolamento da Data API (a prova real roda no Postgres)."""

from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_check_skips_on_non_postgres(db):
    out = StringIO()
    call_command("check_data_api_isolation", stdout=out)
    assert "não se aplica" in out.getvalue()


def test_check_fails_when_data_api_role_has_privilege(db):
    fake_cursor = mock.MagicMock()
    fake_cursor.__enter__.return_value.fetchall.return_value = [
        ("accounts_user", "anon", "SELECT")
    ]
    with (
        mock.patch("django.db.connection.vendor", "postgresql"),
        mock.patch("django.db.connection.cursor", return_value=fake_cursor),
    ):
        with pytest.raises(CommandError, match="anon tem SELECT"):
            call_command("check_data_api_isolation")
