from datetime import timedelta
from academia_core.models import EstudianteProfesorado, EspacioCurricular, Correlatividad

REG_OK_CODIGOS = {"PROMOCION", "APROBADO", "REGULAR"}

def tiene_regularizada(
    insc: EstudianteProfesorado, esp: EspacioCurricular, hasta_fecha=None
) -> bool:
    qs = insc.movimientos.filter(
        espacio=esp, tipo="REG", condicion__codigo__in=REG_OK_CODIGOS
    )
    if hasta_fecha:
        qs = qs.filter(fecha__lte=hasta_fecha)
    return qs.exists()


def tiene_aprobada(
    insc: EstudianteProfesorado, esp: EspacioCurricular, hasta_fecha=None
) -> bool:
    qs1 = insc.movimientos.filter(
        espacio=esp, tipo="REG", condicion__codigo__in={"PROMOCION", "APROBADO"}
    )
    qs2 = insc.movimientos.filter(
        espacio=esp, tipo="FIN", condicion__codigo="REGULAR", nota_num__gte=6
    )
    qs3 = insc.movimientos.filter(
        espacio=esp,
        tipo="FIN",
        condicion__codigo="EQUIVALENCIA",
        nota_texto__iexact="Equivalencia",
    )
    if hasta_fecha:
        qs1 = qs1.filter(fecha__lte=hasta_fecha)
        qs2 = qs2.filter(fecha__lte=hasta_fecha)
        qs3 = qs3.filter(fecha__lte=hasta_fecha)
    return qs1.exists() or qs2.exists() or qs3.exists()


def cumple_correlativas(
    insc: EstudianteProfesorado, esp: EspacioCurricular, tipo: str, fecha=None
):
    reglas = Correlatividad.objects.filter(plan=esp.plan, espacio=esp, tipo=tipo)
    faltan = []
    for r in reglas:
        if r.requiere_espacio:
            reqs = [r.requiere_espacio]
        else:
            reqs = list(
                EspacioCurricular.objects.filter(plan=esp.plan).filter(
                    anio__in=[
                        f"{i}°"
                        for i in range(1, (r.requiere_todos_hasta_anio or 0) + 1)
                    ]
                )
            )
        for req in reqs:
            if r.requisito == "REGULARIZADA":
                ok = tiene_regularizada(insc, req, hasta_fecha=fecha)
            else:
                ok = tiene_aprobada(insc, req, hasta_fecha=fecha)
            if not ok:
                faltan.append((r, req))
    return (len(faltan) == 0), faltan

def tiene_regularidad_vigente(
    insc: EstudianteProfesorado, esp: EspacioCurricular, a_fecha
) -> bool:
    limite = a_fecha - timedelta(days=730)
    return insc.movimientos.filter(
        espacio=esp, tipo="REG", condicion__codigo="REGULAR", fecha__gte=limite
    ).exists()