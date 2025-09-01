from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import HorarioClase

@receiver(m2m_changed, sender=HorarioClase.docentes.through)
def evitar_solape_docente(sender, instance: HorarioClase, action, pk_set, **kwargs):
    # Validamos sólo cuando se van a agregar docentes
    if action not in ("pre_add",) or not pk_set:
        return

    timeslot_id = instance.timeslot_id
    periodo_id = getattr(instance.comision, "periodo_id", None)
    if not timeslot_id or not periodo_id:
        return

    conflictos = (
        HorarioClase.objects
        .filter(timeslot_id=timeslot_id, comision__periodo_id=periodo_id)
        .filter(docentes__id__in=pk_set)
        .exclude(pk=instance.pk)
        .select_related("comision", "timeslot")
        .distinct()
    )
    if conflictos.exists():
        # armamos listado de docentes en conflicto
        from .models import Docente
        nombres = list(Docente.objects.filter(id__in=pk_set).values_list("apellido_nombre", flat=True))
        raise ValidationError(
            f"No se puede asignar docentes {', '.join(nombres)}: ya están asignados en este mismo bloque (mismo período)."
        )