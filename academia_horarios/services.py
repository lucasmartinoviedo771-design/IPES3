# academia_horarios/services.py
from django.apps import apps
from django.core.exceptions import ValidationError

def _solapa(h1_ini, h1_fin, h2_ini, h2_fin) -> bool:
    return (h1_ini < h2_fin) and (h2_ini < h1_fin)

def detectar_conflicto_docente(docente, dia_semana, hora_inicio, hora_fin, excluir_comision_id=None):
    """Chequea choques del docente con otros bloques ese mismo día."""
    HorarioClase = apps.get_model("academia_horarios", "HorarioClase")
    qs = (
        HorarioClase.objects
        .filter(docente=docente, timeslot__dia_semana=dia_semana)
        .select_related("timeslot")
    )
    if excluir_comision_id:
        qs = qs.exclude(comision_id=excluir_comision_id)

    for hc in qs:
        ini = hc.timeslot.inicio
        fin = hc.timeslot.fin
        if _solapa(ini, fin, hora_inicio, hora_fin):
            return hc
    return None

def asignar_docente_a_comision(comision, docente):
    """
    Asigna el docente si NO hay choque de horarios con sus otras comisiones.
    (Sin límite semanal: puede tener todas las horas que quiera.)
    """
    HorarioClase = apps.get_model("academia_horarios", "HorarioClase")
    for hc in HorarioClase.objects.filter(comision=comision).select_related("timeslot"):
        ts = hc.timeslot
        conflicto = detectar_conflicto_docente(
            docente=docente,
            dia_semana=ts.dia_semana,
            hora_inicio=ts.inicio,
            hora_fin=ts.fin,
            excluir_comision_id=comision.id,
        )
        if conflicto:
            raise ValidationError(
                f"Conflicto: el docente ya está asignado en ese rango (comisión {conflicto.comision_id}).",
                code="conflicto_docente",
            )
    comision.docente = docente
    comision.save(update_fields=["docente"])
    return comision

def inscribir_estudiante_en_comision(estudiante, comision):
    """
    Inscribe al estudiante verificando:
    - no duplicado en la misma comisión
    - no choque de horarios con otras comisiones ya inscriptas
    """
    Inscripcion = apps.get_model("academia_core", "InscripcionComision")  # ajustá si tu modelo se llama distinto
    HorarioClase = apps.get_model("academia_horarios", "HorarioClase")

    if Inscripcion.objects.filter(estudiante=estudiante, comision=comision).exists():
        raise ValidationError("Ya estás inscripto en esta comisión.", code="duplicado")

    mis_comisiones = Inscripcion.objects.filter(estudiante=estudiante).values_list("comision_id", flat=True)
    mis_horarios = HorarioClase.objects.filter(comision_id__in=mis_comisiones).select_related("timeslot")
    nuevos = HorarioClase.objects.filter(comision=comision).select_related("timeslot")

    for nuevo in nuevos:
        for viejo in mis_horarios:
            if (nuevo.timeslot.dia_semana == viejo.timeslot.dia_semana) and _solapa(
                nuevo.timeslot.inicio, nuevo.timeslot.fin,
                viejo.timeslot.inicio, viejo.timeslot.fin
            ):
                raise ValidationError("Conflicto de horarios con otra comisión ya inscripta.", code="choque_estudiante")

    return Inscripcion.objects.create(estudiante=estudiante, comision=comision)


# No usamos .env ni settings para topes. Solo evitamos solapamientos de horarios del docente.