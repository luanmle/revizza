from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("suggestions", "0002_suggestionvote")]

    operations = [
        migrations.AddField(
            model_name="suggestion",
            name="proposed_tags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
