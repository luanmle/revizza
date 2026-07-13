import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("discussions", "0002_alter_comment_author"),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reason", models.TextField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("reviewed", "Reviewed")],
                        default="pending",
                        max_length=8,
                    ),
                ),
                (
                    "comment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports",
                        to="discussions.comment",
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="accounts.user",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_reports",
                        to="accounts.user",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(
                fields=["status", "created_at"],
                name="discussions_status_4e21d3_idx",
            ),
        ),
    ]
