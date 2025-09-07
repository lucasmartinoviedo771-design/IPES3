# manage.py seed_bloques
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand

from academia_horarios.models import Bloque, TurnoModel


class Command(BaseCommand):
    help = "Genera bloques de 40' + recreos por turno"

    def handle(self, *args, **opts):
        TurnoModel.objects.get_or_create(slug="maniana", defaults={"nombre": "Mañana"})
        TurnoModel.objects.get_or_create(slug="tarde", defaults={"nombre": "Tarde"})
        TurnoModel.objects.get_or_create(slug="vespertino", defaults={"nombre": "Vespertino"})
        TurnoModel.objects.get_or_create(slug="sabado_am", defaults={"nombre": "Sábado (Mañana)"})

        config = {
            "maniana": dict(inicio=time(8, 0), bloques=6, recreos={3}),
            "tarde": dict(inicio=time(14, 0), bloques=6, recreos={3}),
            "vespertino": dict(inicio=time(18, 0), bloques=5, recreos={3}),
            "sabado_am": dict(inicio=time(8, 0), bloques=4, recreos={0}),
        }

        for slug, cfg in config.items():
            turno = TurnoModel.objects.get(slug=slug)
            Bloque.objects.filter(turno=turno).delete()
            for dia in [0, 1, 2, 3, 4, 5]:  # lun..sab
                h = cfg["inicio"]
                orden = 1
                # Corregido: el bucle original no avanzaba la hora
                for _i in range(cfg["bloques"]):
                    es_recreo_actual = orden in cfg["recreos"]
                    dur_actual = 20 if es_recreo_actual else 40
                    fin_actual = (
                        datetime.combine(date.today(), h) + timedelta(minutes=dur_actual)
                    ).time()

                    # Creamos el bloque principal (o el recreo si toca)
                    Bloque.objects.create(
                        turno=turno,
                        dia_semana=dia,
                        orden=orden,
                        inicio=h,
                        fin=fin_actual,
                        es_recreo=es_recreo_actual,
                    )
                    h = fin_actual
                    orden += 1

                    # Si el que acabamos de crear FUE un recreo, ahora creamos el bloque de clase que le sigue
                    if es_recreo_actual:
                        dur_clase = 40
                        fin_clase = (
                            datetime.combine(date.today(), h) + timedelta(minutes=dur_clase)
                        ).time()
                        Bloque.objects.create(
                            turno=turno,
                            dia_semana=dia,
                            orden=orden,
                            inicio=h,
                            fin=fin_clase,
                            es_recreo=False,
                        )
                        h = fin_clase
                        orden += 1

        self.stdout.write(self.style.SUCCESS("Bloques generados"))
