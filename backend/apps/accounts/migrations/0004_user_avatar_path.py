from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_user_name")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_path",
            field=models.CharField(blank=True, max_length=500, null=True),
        )
    ]
