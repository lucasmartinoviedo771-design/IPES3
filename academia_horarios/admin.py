from django.contrib import admin
from .models import Periodo, MateriaEnPlan, Comision, TimeSlot, HorarioClase, Horario

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ("ciclo_lectivo", "cuatrimestre")
    list_filter = ("ciclo_lectivo", "cuatrimestre")

@admin.register(MateriaEnPlan)
class MateriaEnPlanAdmin(admin.ModelAdmin):
    list_display = ("plan", "materia", "anio", "tipo_dictado", "horas_catedra_semana_1c", "horas_catedra_semana_2c")
    list_filter = ("plan", "anio", "tipo_dictado")

@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ("materia_en_plan", "periodo", "turno", "nombre", "cupo")
    list_filter = ("periodo", "turno", "materia_en_plan__plan", "materia_en_plan__anio")

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("dia_semana", "inicio", "fin")
    list_filter = ("dia_semana",)

@admin.register(HorarioClase)
class HorarioClaseAdmin(admin.ModelAdmin):
    list_display = ("comision", "timeslot", "aula")
    list_filter = ("comision__periodo", "comision__turno")

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('materia', 'dia', 'inicio', 'fin', 'docente', 'aula', 'comision', 'turno')
    list_filter = ('profesorado', 'plan', 'anio', 'dia', 'docente', 'turno')
    search_fields = ('materia__nombre', 'docente__apellido', 'docente__nombre', 'comision', 'aula')
    raw_id_fields = ('materia', 'plan', 'profesorado', 'docente')
    list_per_page = 25
