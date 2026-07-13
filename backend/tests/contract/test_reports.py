"""Contract/admin tests: content reports and review actions (FR-048 to FR-051)."""

import pytest
from django.contrib import admin
from django.contrib.auth.models import User as AdminUser
from django.core import mail
from django.test import RequestFactory, override_settings

from apps.discussions.models import Comment, Report

pytestmark = pytest.mark.django_db


def test_report_note_comment(auth_client, user, make_note):
    comment = Comment.objects.create(author=user, note=make_note(), body="Abusivo")

    response = auth_client.post(
        f"/api/v1/comments/{comment.id}/reports/",
        {"reason": "Ataque pessoal"},
        format="json",
    )

    assert response.status_code == 201
    report = Report.objects.get(pk=response.json()["id"])
    assert report.reporter == user
    assert report.comment == comment
    assert report.reason == "Ataque pessoal"
    assert report.status == Report.Status.PENDING


def test_report_suggestion_comment(auth_client, user, make_suggestion):
    suggestion = make_suggestion()
    comment = Comment.objects.create(
        author=user, suggestion=suggestion, body="Mensagem da sugestão"
    )

    response = auth_client.post(
        f"/api/v1/suggestion-comments/{comment.id}/reports/", {}, format="json"
    )

    assert response.status_code == 201
    assert Report.objects.get().comment == comment


def test_report_requires_authentication(api_client, user, make_note):
    comment = Comment.objects.create(author=user, note=make_note(), body="Conteúdo")

    response = api_client.post(f"/api/v1/comments/{comment.id}/reports/")

    assert response.status_code == 401


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="suporte@example.com",
)
def test_admin_removes_content_and_emails_author(user, make_note):
    comment = Comment.objects.create(author=user, note=make_note(), body="Remover")
    report = Report.objects.create(
        reporter=user, comment=comment, reason="Motivo da remoção"
    )
    request = RequestFactory().post("/admin/")
    request.user = AdminUser.objects.create_superuser(
        username="admin", email="admin@example.com", password="senha"
    )
    model_admin = admin.site._registry[Report]

    model_admin.remove_reported_content(request, Report.objects.filter(pk=report.pk))

    assert not Comment.objects.filter(pk=comment.pk).exists()
    report.refresh_from_db()
    assert report.status == Report.Status.REVIEWED
    assert report.comment is None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert "Motivo da remoção" in mail.outbox[0].body


def test_admin_can_suspend_content_author(user, make_note):
    comment = Comment.objects.create(author=user, note=make_note(), body="Abusivo")
    report = Report.objects.create(reporter=user, comment=comment)
    request = RequestFactory().post("/admin/")
    request.user = AdminUser.objects.create_superuser(
        username="admin2", email="admin2@example.com", password="senha"
    )
    model_admin = admin.site._registry[Report]

    model_admin.suspend_content_author(
        request, Report.objects.filter(pk=report.pk)
    )

    user.refresh_from_db()
    report.refresh_from_db()
    assert user.is_suspended is True
    assert report.status == Report.Status.REVIEWED
