"""Unit tests: scheduler de deleção de contas (idempotência, isolamento, auditoria)."""

import logging
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts import jobs
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _expire(user, days_ago=8):
    user.deletion_requested_at = timezone.now() - timedelta(days=days_ago)
    user.save(update_fields=["deletion_requested_at"])


def test_running_command_twice_is_idempotent(user, monkeypatch):
    _expire(user)
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.delete_user", lambda auth_id: None
    )

    first = jobs.delete_expired_accounts()
    second = jobs.delete_expired_accounts()

    assert first == 1
    assert second == 0
    assert not User.objects.filter(pk=user.pk).exists()


def test_accounts_within_grace_period_are_untouched(user, monkeypatch):
    _expire(user, days_ago=3)
    calls = []
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.delete_user", lambda auth_id: calls.append(auth_id)
    )

    deleted = jobs.delete_expired_accounts()

    assert deleted == 0
    assert calls == []
    assert User.objects.filter(pk=user.pk).exists()


def test_one_account_failure_does_not_block_others(user, make_user, monkeypatch):
    ok1 = user
    fail = make_user("falha@example.com")
    ok2 = make_user("ok2@example.com")
    for account in (ok1, fail, ok2):
        _expire(account)

    def _delete_user(auth_id):
        if auth_id == str(fail.auth_id):
            raise RuntimeError("supabase indisponível")

    monkeypatch.setattr("apps.accounts.supabase_gateway.delete_user", _delete_user)

    deleted = jobs.delete_expired_accounts()

    assert deleted == 2
    assert not User.objects.filter(pk=ok1.pk).exists()
    assert not User.objects.filter(pk=ok2.pk).exists()
    assert User.objects.filter(pk=fail.pk).exists()


def test_failed_account_is_retried_next_run(user, make_user, monkeypatch):
    ok1 = user
    fail = make_user("falha@example.com")
    ok2 = make_user("ok2@example.com")
    for account in (ok1, fail, ok2):
        _expire(account)

    def _delete_user_raising(auth_id):
        if auth_id == str(fail.auth_id):
            raise RuntimeError("supabase indisponível")

    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.delete_user", _delete_user_raising
    )
    jobs.delete_expired_accounts()
    assert User.objects.filter(pk=fail.pk).exists()

    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.delete_user", lambda auth_id: None
    )
    deleted = jobs.delete_expired_accounts()

    assert deleted == 1
    assert not User.objects.filter(pk=fail.pk).exists()


def test_command_logs_deleted_and_failed_counts(user, make_user, monkeypatch, caplog):
    ok = user
    fail = make_user("falha@example.com")
    for account in (ok, fail):
        _expire(account)

    def _delete_user(auth_id):
        if auth_id == str(fail.auth_id):
            raise RuntimeError("supabase indisponível")

    monkeypatch.setattr("apps.accounts.supabase_gateway.delete_user", _delete_user)

    with caplog.at_level(logging.INFO, logger="apps.accounts.jobs"):
        call_command("delete_expired_accounts")

    audit_records = [r for r in caplog.records if "deleted=" in r.getMessage()]
    assert audit_records
    message = audit_records[0].getMessage()
    assert "deleted=1" in message
    assert "failed=1" in message
