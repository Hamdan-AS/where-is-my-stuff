from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_add_public_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="lat",
            field=models.DecimalField(decimal_places=8, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="report",
            name="lng",
            field=models.DecimalField(decimal_places=8, max_digits=11, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="match",
            name="meeting_place",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]