from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("academia_core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="carrera",
            name="abreviatura",
            field=models.CharField(
                "Abreviatura",
                max_length=50,  # igual que en tu models.py
                null=True,      # para poder crearla sin default
                blank=True,
            ),
        ),
    ]
