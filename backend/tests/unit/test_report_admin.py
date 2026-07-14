"""T145: remoção de conteúdo denunciado sobrevive a falha de notificação (FR-050)."""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite

from apps.discussions.admin import ReportAdmin
from apps.discussions.models import Comment, Report

pytestmark = pytest.mark.django_db


def test_mail_failure_does_not_abort_action_mid_queryset(user, make_note, monkeypatch):
    note = make_note()
    reports = [
        Report.objects.create(
            reporter=user,
            reason="spam",
            comment=Comment.objects.create(author=user, body=f"c{i}", note=note),
        )
        for i in range(2)
    ]
    monkeypatch.setattr(
        "apps.discussions.admin.send_mail",
        mock.Mock(side_effect=OSError("SMTP fora do ar")),
    )
    admin_instance = ReportAdmin(Report, AdminSite())
    request = SimpleNamespace(user=SimpleNamespace(email=user.email))

    with mock.patch.object(ReportAdmin, "message_user") as message_user:
        admin_instance.remove_reported_content(request, Report.objects.all())

    assert Comment.objects.count() == 0  # os dois conteúdos foram removidos
    for report in reports:
        report.refresh_from_db()
        assert report.status == Report.Status.REVIEWED
        assert report.comment is None
    message_user.assert_called_once()
    assert message_user.call_args.kwargs["level"] == messages.WARNING
