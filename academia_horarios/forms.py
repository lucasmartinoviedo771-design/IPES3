# academia_horarios/forms.py
from __future__ import annotations

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from .models import HorarioClase, TimeSlot, Comision, Turno

# Tomamos Docente del app correcto
Docente = apps.get_model("academia_core", "Docente")


class HorarioInlineForm(forms.Form):
    comision = forms.IntegerField(widget=forms.HiddenInput)

    # Elegimos un bloque (TimeSlot) ya definido
    timeslot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all().order_by("dia_semana", "inicio"),
        label="Bloque"
    )

    aula = forms.CharField(max_length=64, required=False, label="Aula")

    docentes = forms.ModelMultipleChoiceField(
        queryset=Docente.objects.all().order_by("apellido", "nombre"),
        required=False,
        label="Docentes"
    )

    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Observaciones"
    )

    def clean(self):
        cleaned = super().clean()
        # Si necesitás validaciones extras, agregalas acá
        return cleaned

    def save(self, comision: Comision):
        """
        Crea un HorarioClase para la comisión dada, con el bloque seleccionado.
        Respeta la unicidad (comision, timeslot).
        """
        ts = self.cleaned_data["timeslot"]
        aula = (self.cleaned_data.get("aula") or "").strip()
        docentes = self.cleaned_data.get("docentes") or []
        obs = (self.cleaned_data.get("observaciones") or "").strip()

        # Evitar duplicar el mismo bloque para la misma comisión
        if HorarioClase.objects.filter(comision=comision, timeslot=ts).exists():
            raise ValidationError(
                {"timeslot": "Ya existe un bloque para esta comisión en ese horario."}
            )

        obj = HorarioClase.objects.create(
            comision=comision,
            timeslot=ts,
            aula=aula,
            observaciones=obs,
        )
        if docentes:
            obj.docentes.set(docentes)
        return obj
