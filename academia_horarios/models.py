from django.db import models
from django.core.exceptions import ValidationError
from datetime import time

from academia_core.models import (
    Docente,
    Profesorado,
    PlanEstudios,        # tu “Plan”
    EspacioCurricular,   # tu “Materia”
    Carrera, # Added Carrera for Horario model
    Aula, # Added Aula for Horario model
)

# ======= Catálogos/Períodos =======
class Turno(models.TextChoices):
    MANANA = "manana", "Mañana"
    TARDE = "tarde", "Tarde"
    VESPERTINO = "vespertino", "Vespertino"
    SABADO = "sabado", "Sábado"

class Periodo(models.Model):
    ciclo_lectivo = models.PositiveIntegerField()
    cuatrimestre = models.PositiveSmallIntegerField(choices=((1, "1°"),(2, "2°")))
    def __str__(self): return f"{self.ciclo_lectivo} - {self.cuatrimestre}°C"
    class Meta:
        db_table = "academia_horarios_periodo"
        unique_together = ("ciclo_lectivo", "cuatrimestre")

# ======= Oferta =======
class TipoDictado(models.TextChoices):
    ANUAL = "ANUAL", "Anual"
    CUATRIMESTRAL = "CUATRIMESTRAL", "Cuatrimestral"

class MateriaEnPlan(models.Model):
    plan = models.ForeignKey(PlanEstudios, on_delete=models.PROTECT)
    materia = models.ForeignKey(EspacioCurricular, on_delete=models.PROTECT)
    anio = models.PositiveSmallIntegerField()
    tipo_dictado = models.CharField(max_length=16, choices=TipoDictado.choices)
    horas_catedra_semana_1c = models.PositiveSmallIntegerField(default=0)
    horas_catedra_semana_2c = models.PositiveSmallIntegerField(default=0)
    horas_catedra = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Cantidad semanal de horas cátedra (40’). Dejar vacío = sin tope."
    )
    def __str__(self): return f"{self.plan} — {self.materia} — {self.anio}°"
    class Meta:
        db_table = "academia_horarios_materiaenplan"
        unique_together = ("plan", "materia", "anio")

class Comision(models.Model):
    materia_en_plan = models.ForeignKey(MateriaEnPlan, on_delete=models.PROTECT)
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT)
    turno = models.CharField(max_length=16, choices=Turno.choices)
    nombre = models.CharField(max_length=16, default="Única")
    cupo = models.PositiveSmallIntegerField(default=0)
    # NUEVO:
    seccion = models.CharField(max_length=2, default='A')   # A, B, C...

    def horas_catedra_tope(self):
        return hc_requeridas(self.materia_en_plan, self.periodo)

    def horas_asignadas_en_periodo(self) -> int:
        return self.horarios.count()

    def horas_restantes_en_periodo(self):
        tope = self.horas_catedra_tope()
        if tope is None:
            return None
        return max(tope - self.horas_asignadas_en_periodo(), 0)

    def __str__(self):
        p = self.materia_en_plan
        return f"{p.plan.profesorado} {p.anio}° — {p.materia} — {self.periodo} — {self.nombre} ({self.get_turno_display()})"
    class Meta:
        db_table = "academia_horarios_comision"
        # unique_together = ("materia_en_plan", "periodo", "nombre") # OLD
        unique_together = ("materia_en_plan", "periodo", "seccion") # NEW

class TimeSlot(models.Model):
    dia_semana = models.PositiveSmallIntegerField()
    inicio = models.TimeField()
    fin = models.TimeField()

    DIA_CHOICES = [
        (1, "Lunes"),
        (2, "Martes"),
        (3, "Miércoles"),
        (4, "Jueves"),
        (5, "Viernes"),
        (6, "Sábado"),
        (7, "Domingo"),
    ]

    def get_dia_semana_display(self):
        dias = {i: lbl for i, lbl in self.DIA_CHOICES}
        return dias.get(self.dia_semana, f"Día {self.dia_semana}")

    def __str__(self): return f"{self.get_dia_semana_display()} {self.inicio}-{self.fin}"
    class Meta:
        db_table = "academia_horarios_timeslot"
        indexes = [models.Index(fields=["dia_semana", "inicio", "fin"])]
        constraints = [models.CheckConstraint(check=models.Q(inicio__lt=models.F("fin")), name="timeslot_inicio_lt_fin")]

# Helper function for overlaps
def overlaps(a1, a2, b1, b2):
    # “se pisan” si una empieza antes de que termine la otra y viceversa
    return a1 < b2 and b1 < a2

class Horario(models.Model):
    # This is the new Horario model based on the user's pseudo-code
    # It assumes a ForeignKey to Docente, not ManyToManyField
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT)
    plan = models.ForeignKey(PlanEstudios, on_delete=models.PROTECT)
    materia = models.ForeignKey(EspacioCurricular, on_delete=models.PROTECT)
    turno = models.CharField(max_length=16, choices=Turno.choices)
    # NUEVO:
    seccion = models.CharField(max_length=2, default='A')   # para distinguir 1ºA, 1ºB en el horario
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True)
    aula = models.ForeignKey(Aula, on_delete=models.SET_NULL, null=True, blank=True)
    dia = models.PositiveSmallIntegerField(choices=TimeSlot.DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    observaciones = models.TextField(blank=True, default="")
    activo = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        errors = {}

        # 1) inicio < fin
        if self.hora_fin <= self.hora_inicio:
            errors['hora_fin'] = 'La hora fin debe ser posterior a la hora inicio.'

        # 2) choques del DOCENTE (si está designado)
        if self.docente:
            qs = Horario.objects.filter(docente=self.docente, dia=self.dia)
            if self.pk: qs = qs.exclude(pk=self.pk)
            for h in qs:
                if overlaps(self.hora_inicio, self.hora_fin, h.hora_inicio, h.hora_fin):
                    errors['docente'] = f'El docente {self.docente.nombre} ya tiene un horario en esa franja.'
                    break

        # 3) choques del AULA (si se indicó)
        if self.aula:
            qs = Horario.objects.filter(aula=self.aula, dia=self.dia)
            if self.pk: qs = qs.exclude(pk=self.pk)
            for h in qs:
                if overlaps(self.hora_inicio, self.hora_fin, h.hora_inicio, h.hora_fin):
                    errors['aula'] = 'El aula ya está ocupada en esa franja.'
                    break

        if errors:
            raise ValidationError(errors)

    def __str__(self): return f"{self.materia} - {self.dia} {self.hora_inicio}-{self.hora_fin}"

    class Meta:
        db_table = "academia_horarios_horario"


class HorarioClase(models.Model):
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE, related_name="horarios")
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT)
    aula = models.CharField(max_length=64, blank=True, default="")
    docentes = models.ManyToManyField(Docente, blank=True)
    observaciones = models.TextField(blank=True, default="")

    def clean(self):
        super().clean()
        if not self.comision_id or not self.timeslot_id:
            return

        c = self.comision

        # 1) Validar solapamiento de bloques (misma materia, año, plan, etc)
        mep = c.materia_en_plan
        conflicto_bloque = (
            HorarioClase.objects
            .filter(
                timeslot=self.timeslot,
                comision__periodo=c.periodo,
                comision__materia_en_plan__anio=mep.anio,
                comision__materia_en_plan__plan__profesorado=mep.plan.profesorado,
            )
            .exclude(pk=self.pk)
            .exists()
        )
        if conflicto_bloque:
            raise ValidationError({
                "timeslot": (
                    "Bloque ocupado para este Profesorado/Plan/Período/Año. "
                    "Elegí otro bloque."
                )
            })

        # 2) Validar tope de horas cátedra de la comisión
        tope = c.horas_catedra_tope()
        if tope is not None:
            # Solo chequear al crear, ya que al editar no se suman horas.
            if self.pk is None:
                asignadas = c.horas_asignadas_en_periodo()
                if asignadas >= tope:
                    raise ValidationError({
                        "timeslot": f"Se ha alcanzado el tope de {tope} horas cátedra para esta comisión."
                    })

    class Meta:
        db_table = "academia_horarios_horarioclase"
        constraints = [
            models.UniqueConstraint(
                fields=["comision", "timeslot"],
                name="uniq_horario_por_comision_bloque",
            ),
        ]

# ======= Reglas de grilla (40' + recreos) y HC =======
GRILLAS = {
    "manana": {
        "start": time(7,45), "end": time(12,45),
        "breaks": [(time(9,5), time(9,15)), (time(10,35), time(10,45))],
    },
    "tarde": {
        "start": time(13,0), "end": time(18,0),
        "breaks": [(time(14,20), time(14,30)), (time(15,50), time(16,0))],
    },
    "vespertino": {
        "start": time(18,10), "end": time(23,10),
        "breaks": [(time(19,30), time(19,40)), (time(21,0), time(21,10))],
    },
    "sabado": {
        "start": time(9,0), "end": time(14,0),
        "breaks": [(time(10,20), time(10,30)), (time(11,50), time(12,0))],
    },
}
BLOCK_MIN = 40

def hc_asignadas(comision: Comision) -> int:
    return comision.horas_asignadas_en_periodo()

def hc_requeridas(mep: MateriaEnPlan, periodo: Periodo) -> int | None:
    tope = None
    # 1) Si tenés campos por cuatrimestre en MateriaEnPlan
    if periodo and hasattr(mep, "horas_catedra_semana_1c") and hasattr(mep, "horas_catedra_semana_2c"):
        if periodo.cuatrimestre == 1 and getattr(mep, "horas_catedra_semana_1c", None) is not None:
            tope = mep.horas_catedra_semana_1c
        elif periodo.cuatrimestre in (2, 3) and getattr(mep, "horas_catedra_semana_2c", None) is not None:
            tope = mep.horas_catedra_semana_2c

    # 2) Tope general en MateriaEnPlan
    if tope is None and getattr(mep, "horas_catedra", None) is not None:
        tope = mep.horas_catedra

    # 3) Fallback a EspacioCurricular.horas_catedra
    materia = getattr(mep, "materia", None)
    if tope is None and materia and getattr(materia, "horas_catedra", None) is not None:
        tope = materia.horas_catedra

    return tope

def _mins(t: time) -> int:
    return t.hour * 60 + t.minute

def es_multiplo_40(t: time) -> bool:
    return (_mins(t) - _mins(GRILLAS["manana"]["start"])) % BLOCK_MIN == 0

def atraviesa_recreo(turno: str, inicio: time, fin: time) -> bool:
    for a, b in GRILLAS[turno]["breaks"]:
        if inicio < b and fin > a:
            return True
    return False

def dentro_de_jornada(turno: str, inicio: time, fin: time) -> bool:
    s, e = GRILLAS[turno]["start"], GRILLAS[turno]["end"]
    return (inicio >= s) and (fin <= e)

def minutos(ts: TimeSlot) -> int:
    return _mins(ts.fin) - _mins(ts.inicio)


# =============================================================================
# NUEVOS MODELOS PARA GESTION DE HORARIOS (propuesta escalable)
# =============================================================================

class TurnoModel(models.Model):
    nombre = models.CharField(max_length=50)
    slug   = models.SlugField(unique=True)

    def __str__(self):
        return self.nombre

class Bloque(models.Model):
    turno       = models.ForeignKey(TurnoModel, on_delete=models.CASCADE)
    dia_semana  = models.IntegerField(choices=[(0,'Lun'),(1,'Mar'),(2,'Mié'),(3,'Jue'),(4,'Vie'),(5,'Sáb')])
    orden       = models.IntegerField()
    inicio      = models.TimeField()
    fin         = models.TimeField()
    es_recreo   = models.BooleanField(default=False)

    class Meta:
        unique_together = ('turno','dia_semana','orden')

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.inicio:%H:%M}-{self.fin:%H:%M}"

class Catedra(models.Model):
    materia_en_plan = models.ForeignKey(MateriaEnPlan, on_delete=models.CASCADE)
    comision        = models.ForeignKey(Comision, on_delete=models.CASCADE)
    turno           = models.ForeignKey(TurnoModel, on_delete=models.PROTECT)
    horas_semanales = models.PositiveSmallIntegerField()
    permite_solape_interno = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.materia_en_plan} / {self.comision.nombre}"

class CatedraHorario(models.Model):
    catedra = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='bloques')
    bloque  = models.ForeignKey(Bloque, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('catedra','bloque')

class DocenteAsignacion(models.Model):
    CONDICION = (('INTERINO','Interino'), ('SUPLENTE','Suplente'))
    catedra     = models.ForeignKey(Catedra, on_delete=models.CASCADE, related_name='asignaciones')
    docente     = models.ForeignKey('academia_core.Docente', on_delete=models.PROTECT)
    condicion   = models.CharField(max_length=10, choices=CONDICION)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(null=True, blank=True)
    activa      = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.docente} en {self.catedra} ({self.get_condicion_display()})"

class DocenteCobertura(models.Model):
    asignacion = models.ForeignKey(DocenteAsignacion, on_delete=models.CASCADE, related_name='coberturas')
    bloque     = models.ForeignKey(Bloque, on_delete=models.CASCADE)