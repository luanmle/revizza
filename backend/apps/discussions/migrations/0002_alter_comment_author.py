import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("discussions", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="comments",
                to="accounts.user",
            ),
        ),
    ]
