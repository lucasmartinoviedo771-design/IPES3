from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("academia_core", "0002_add_abreviatura_to_carrera"),
    ]

    operations = [
        migrations.AddField(
            model_name="carrera",
            name="plan_vigente",
            field=models.ForeignKey(
                to="academia_core.planestudios",   # si PlanEstudios está en este mismo app
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="carreras_vigentes",
                verbose_name="Plan vigente",
            ),
        ),
    ]
