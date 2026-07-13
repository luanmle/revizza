from django.conf import settings
from django.contrib import admin
from django.core.mail import send_mail

from apps.accounts.models import User

from .models import Comment, Report


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "created_at", "edited_at"]
    search_fields = ["body", "author__email"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "reporter", "comment", "created_at"]
    list_filter = ["status"]
    search_fields = ["reason", "reporter__email", "comment__body"]
    actions = ["remove_reported_content", "suspend_content_author"]

    def _reviewer(self, request):
        return User.objects.filter(email__iexact=request.user.email).first()

    @admin.action(description="Remover conteúdo denunciado e notificar autor")
    def remove_reported_content(self, request, queryset):
        for report in queryset.select_related("comment__author"):
            comment = report.comment
            author = comment.author if comment else None
            reason = report.reason or "O conteúdo violou as regras da comunidade."
            if comment:
                comment.delete()
                report.comment = None
            report.status = Report.Status.REVIEWED
            report.reviewed_by = self._reviewer(request)
            report.save(
                update_fields=["comment", "status", "reviewed_by", "updated_at"]
            )
            if author and author.email:
                send_mail(
                    "Conteúdo removido no AnkiHub Brasil",
                    f"Seu conteúdo foi removido após revisão. Motivo: {reason}",
                    settings.DEFAULT_FROM_EMAIL,
                    [author.email],
                )

    @admin.action(description="Suspender autor do conteúdo denunciado")
    def suspend_content_author(self, request, queryset):
        reviewer = self._reviewer(request)
        for report in queryset.select_related("comment__author"):
            if report.comment and report.comment.author:
                report.comment.author.is_suspended = True
                report.comment.author.save(
                    update_fields=["is_suspended", "updated_at"]
                )
            report.status = Report.Status.REVIEWED
            report.reviewed_by = reviewer
            report.save(update_fields=["status", "reviewed_by", "updated_at"])
