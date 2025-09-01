from django import forms
from django.core.exceptions import ValidationError
from .models import HorarioClase, TimeSlot, Comision, Docente, Turno
from . import services  # tu detector de conflictos

DIAS_CHOICES = [
    (1, "Lunes"),
    (2, "Martes"),
    (3, "Miércoles"),
    (4, "Jueves"),
    (5, "Viernes"),
    (6, "Sábado"),
    (7, "Domingo"),
]

TURNOS = (
    ("M", "Mañana"),
    ("T", "Tarde"),
    ("V", "Vespertino"),
    ("S", "Sábado"),
)

class HorarioInlineForm(forms.Form):
    turno = forms.ChoiceField(
        choices=(("", "— (todos) —"),) + TURNOS,
        required=False,
    )
    dia = forms.ChoiceField(
        choices=(("", "— (todos) —"),) + tuple((str(i), lbl) for i, lbl in TimeSlot.DIA_CHOICES),
        required=True,
    )
    bloque = forms.ModelChoiceField(
        queryset=TimeSlot.objects.none(),
        required=True,
        empty_label="— elegí un bloque —",
    )
    aula = forms.CharField(required=False)
    docentes = forms.ModelMultipleChoiceField(
        queryset=None,  # lo ponés como estés cargando docentes
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # si ya tenés un queryset global de docentes, dejalo así:
        self.fields["docentes"].queryset = Docente.objects.order_by("apellido_nombre")

        # Si vino POST, podes ajustar el queryset del bloque a lo que corresponde
        data = self.data or self.initial
        t = (data.get("turno") or "").strip()
        d = (data.get("dia") or "").strip()

        qs = TimeSlot.objects.all()
        if d:
            qs = qs.filter(dia_semana=int(d))

        # Filtro opcional por turno (por horas):
        if t:
            if t == "S":
                qs = qs.filter(dia_semana=6)
            elif t == "M":
                qs = qs.filter(inicio__lt="12:45")
            elif t == "T":
                qs = qs.filter(inicio__gte="13:00", inicio__lt="18:01")
            elif t == "V":
                qs = qs.filter(inicio__gte="18:10")

        self.fields["bloque"].queryset = qs.order_by("inicio")

    def clean(self):
        cd = super().clean()
        ts = cd.get("bloque")
        d  = cd.get("dia")
        if ts and d and ts.dia_semana != int(d):
            self.add_error("bloque", "El bloque no coincide con el día seleccionado.")
        return cd

    def save(self, comision):
        hc = HorarioClase.objects.create(
            comision=comision,
            timeslot=self.cleaned_data["bloque"],
            aula=self.cleaned_data.get("aula") or ""
        )
        if self.cleaned_data.get("docentes"):
            hc.docentes.set(self.cleaned_data["docentes"])
        return hc

class HorarioClaseForm(forms.ModelForm):
    class Meta:
        model = HorarioClase
        fields = ["timeslot", "aula", "docentes"]

    def clean(self):
        cleaned = super().clean()
        timeslot = cleaned.get("timeslot")
        docentes = cleaned.get("docentes")  # esto es un queryset de Docente

        # Si no hay timeslot o comision todavía, no validamos
        if not timeslot or not self.instance or not self.instance.comision_id:
            return cleaned

        # chequeo por cada docente seleccionado
        for d in docentes:
            conflicto = services.detectar_conflicto_docente(
                docente=d,
                dia_semana=timeslot.dia_semana,
                hora_inicio=timeslot.inicio,
                hora_fin=timeslot.fin,
                excluir_comision_id=self.instance.comision_id,
            )
            if conflicto:
                raise ValidationError({
                    "docentes": f"{d} ya tiene una comisión en ese horario (id {conflicto.comision_id})."
                })

        return cleaned