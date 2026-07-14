from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_revoke_data_api_access")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="name",
            field=models.CharField(blank=True, default="", max_length=120),
        )
    ]
