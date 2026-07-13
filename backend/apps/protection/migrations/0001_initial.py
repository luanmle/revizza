import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts", "0001_initial"),
        ("catalog", "0003_subscription"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProtectedFieldConfig",
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
                ("field_name", models.CharField(max_length=200)),
                (
                    "deck",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="protected_fields",
                        to="catalog.deck",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="protected_fields",
                        to="accounts.user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProtectedTagConfig",
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
                ("tag", models.CharField(max_length=200)),
                (
                    "deck",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="protected_tags",
                        to="catalog.deck",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="protected_tags",
                        to="accounts.user",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="protectedfieldconfig",
            constraint=models.UniqueConstraint(
                fields=("user", "deck", "field_name"),
                name="unique_protected_field_per_user_deck",
            ),
        ),
        migrations.AddConstraint(
            model_name="protectedtagconfig",
            constraint=models.UniqueConstraint(
                fields=("user", "deck", "tag"),
                name="unique_protected_tag_per_user_deck",
            ),
        ),
    ]
