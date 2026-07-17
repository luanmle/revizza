from django.db import migrations, models


def backfill_ready(apps, schema_editor):
    apps.get_model("notes", "MediaFile").objects.update(status="ready")


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0002_note_anki_deck_path_notetype_structure_changed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="mediafile",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_upload", "Pending upload"),
                    ("ready", "Ready"),
                ],
                default="ready",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_ready, migrations.RunPython.noop),
    ]
