from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from academia_horarios.models import Bloque
from academia_horarios.models import TurnoModel as Turno

# === TUS HORARIOS (exactos, sin tocar) ===
TURNOS = {
    "m": (time(7, 45), time(12, 45)),
    "t": (time(13, 0), time(18, 0)),
    "v": (time(18, 10), time(23, 10)),
    "s": (time(9, 0), time(14, 0)),
}

GRILLAS = {
    "manana": {
        "start": time(7, 45),
        "end": time(12, 45),
        "breaks": [(time(9, 5), time(9, 15)), (time(10, 35), time(10, 45))],
    },
    "tarde": {
        "start": time(13, 0),
        "end": time(18, 0),
        "breaks": [(time(14, 20), time(14, 30)), (time(15, 50), time(16, 0))],
    },
    "vespertino": {
        "start": time(18, 10),
        "end": time(23, 10),
        "breaks": [(time(19, 30), time(19, 40)), (time(21, 0), time(21, 10))],
    },
    "sabado": {
        "start": time(9, 0),
        "end": time(14, 0),
        "breaks": [(time(10, 20), time(10, 30)), (time(11, 50), time(12, 0))],
    },
}

BLOCK_MIN = 40


def t2dt(t: time) -> datetime:
    return datetime.combine(date.today(), t)


def dt2t(dt: datetime) -> time:
    return dt.time()


def cortar_en_bloques_de_40(inicio: time, fin: time) -> list[tuple[time, time]]:
    start_dt = t2dt(inicio)
    end_dt = t2dt(fin)
    dur = end_dt - start_dt
    total_min = int(dur.total_seconds() // 60)
    if total_min % BLOCK_MIN != 0:
        raise ValueError(
            f"El tramo {inicio}-{fin} no es múltiplo de {BLOCK_MIN} min (total={total_min})."
        )

    bloques = []
    cur = start_dt
    while cur < end_dt:
        nx = cur + timedelta(minutes=BLOCK_MIN)
        bloques.append((dt2t(cur), dt2t(nx)))
        cur = nx
    return bloques


def construir_linea_de_tiempo(grilla: dict) -> list[tuple[time, time, bool]]:
    start = grilla["start"]
    end = grilla["end"]
    breaks = grilla.get("breaks") or []

    timeline = []
    cursor = start

    # Ordenar recreos para procesar en orden
    sorted_breaks = sorted(breaks, key=lambda x: x[0])

    for b_ini, b_fin in sorted_breaks:
        if cursor < b_ini:
            timeline += [(a, b, False) for (a, b) in cortar_en_bloques_de_40(cursor, b_ini)]
        timeline.append((b_ini, b_fin, True))
        cursor = b_fin

    if cursor < end:
        timeline += [(a, b, False) for (a, b) in cortar_en_bloques_de_40(cursor, end)]

    return timeline


class Command(BaseCommand):
    help = "Genera Turnos y Bloques (40') con recreos, usando la grilla que definió el usuario."

    @transaction.atomic
    def handle(self, *args, **opts):
        turnos_info = [
            ("m", "manana", "Mañana", "manana"),
            ("t", "tarde", "Tarde", "tarde"),
            ("v", "vespertino", "Vespertino", "vespertino"),
            ("s", "sabado", "Sábado", "sabado"),
        ]

        slug2turno = {}
        for _code, slug, nombre, _gkey in turnos_info:
            turno, _ = Turno.objects.update_or_create(
                slug=slug,
                defaults={"nombre": nombre},
            )
            slug2turno[slug] = turno

        self.stdout.write("Borrando bloques existentes...")
        Bloque.objects.all().delete()

        for _code, slug, _nombre, gkey in turnos_info:
            turno = slug2turno[slug]
            gr = GRILLAS[gkey]
            timeline = construir_linea_de_tiempo(gr)

            if slug == "sabado":
                dias = [5]
            else:
                dias = [0, 1, 2, 3, 4]

            for dia in dias:
                orden = 1
                for ini, fin, es_rec in timeline:
                    Bloque.objects.create(
                        turno=turno,
                        dia_semana=dia,
                        orden=orden,
                        inicio=ini,
                        fin=fin,
                        es_recreo=es_rec,
                    )
                    orden += 1
        self.stdout.write(self.style.SUCCESS("Turnos y Bloques generados correctamente."))
