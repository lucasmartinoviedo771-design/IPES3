# academia_core/admin.py
from django.contrib import admin

from .models import (
    Carrera,
    Correlatividad,
    EspacioCurricular,
    Estudiante,
    EstudianteProfesorado,
    InscripcionEspacio,
    Materia,
    PlanEstudios,
    UserProfile,
)


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ("id", "apellido", "nombre", "dni")
    search_fields = ("apellido", "nombre", "dni")
    ordering = ("apellido", "nombre")


# ---------------------------------------------------------------------
# Carrera
# ---------------------------------------------------------------------
@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    # Usamos campos 100% existentes y seguros
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)


# ---------------------------------------------------------------------
# Plan de estudios
# ---------------------------------------------------------------------
@admin.register(PlanEstudios)
class PlanEstudiosAdmin(admin.ModelAdmin):
    list_display = ("id", "carrera", "resolucion", "vigente")
    list_filter = ("vigente", "carrera")
    search_fields = ("resolucion", "carrera__nombre")
    ordering = ("carrera__nombre", "resolucion")


# ---------------------------------------------------------------------
# Materia
# ---------------------------------------------------------------------
@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)


# ---------------------------------------------------------------------
# Espacio Curricular
#   Importante: NO usar 'nombre' (no existe en EspacioCurricular);
#   mostrar la materia del espacio.
# ---------------------------------------------------------------------
@admin.register(EspacioCurricular)
class EspacioCurricularAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "materia", "anio", "cuatrimestre")
    list_filter = ("plan", "anio", "cuatrimestre")
    search_fields = ("materia__nombre", "plan__resolucion", "plan__carrera__nombre")
    autocomplete_fields = ("plan", "materia")
    ordering = ("plan__carrera__nombre", "anio", "cuatrimestre", "materia__nombre")


# ---------------------------------------------------------------------
# Correlatividad
# ---------------------------------------------------------------------
@admin.register(Correlatividad)
class CorrelatividadAdmin(admin.ModelAdmin):
    list_display = ("id", "espacio", "requisito", "tipo")
    search_fields = ("espacio__materia__nombre", "requiere_espacio__materia__nombre")
    autocomplete_fields = ("espacio", "requiere_espacio")
    ordering = (
        "espacio__plan__carrera__nombre",
        "espacio__anio",
        "espacio__cuatrimestre",
        "espacio__materia__nombre",
    )


# ---------------------------------------------------------------------
# Inscripciones y estudiantes (si existen en tu app)
# ---------------------------------------------------------------------
@admin.register(InscripcionEspacio)
class InscripcionEspacioAdmin(admin.ModelAdmin):
    list_display = ("id", "inscripcion", "espacio", "estado")
    search_fields = (
        "inscripcion__estudiante__apellido",
        "inscripcion__estudiante__nombre",
        "espacio__materia__nombre",
    )
    autocomplete_fields = ("inscripcion", "espacio")
    ordering = (
        "espacio__plan__carrera__nombre",
        "espacio__anio",
        "espacio__cuatrimestre",
        "espacio__materia__nombre",
    )


@admin.register(EstudianteProfesorado)
class EstudianteProfesoradoAdmin(admin.ModelAdmin):
    list_display = ("id", "estudiante", "carrera")
    search_fields = (
        "estudiante__apellido",
        "estudiante__nombre",
        "estudiante__dni",
        "carrera__nombre",
    )
    autocomplete_fields = ("carrera", "estudiante")
    ordering = ("estudiante__apellido", "estudiante__nombre")


# ---------------------------------------------------------------------
# Perfil de usuario (si corresponde)
# ---------------------------------------------------------------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("carreras_permitidas",)
