import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("suggestions", "0003_suggestion_proposed_tags")]

    operations = [
        migrations.AlterField(
            model_name="suggestion",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="suggestions",
                to="accounts.user",
            ),
        ),
    ]
