import django.db.models.deletion
from django.db import migrations, models


def backfill_creator(apps, schema_editor):
    Deck = apps.get_model("catalog", "Deck")
    DeckModerator = apps.get_model("catalog", "DeckModerator")
    for deck in Deck.objects.filter(creator__isnull=True).iterator():
        moderator = (
            DeckModerator.objects.filter(
                deck=deck, status="active", invited_by__isnull=True
            )
            .order_by("created_at")
            .first()
        )
        if moderator:
            deck.creator_id = moderator.user_id
            deck.save(update_fields=["creator"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("catalog", "0006_subscription_last_synced_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_decks",
                to="accounts.user",
            ),
        ),
        migrations.AddField(
            model_name="deck",
            name="is_official",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_creator, migrations.RunPython.noop),
    ]
