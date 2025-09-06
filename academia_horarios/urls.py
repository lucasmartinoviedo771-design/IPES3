from django.urls import path
from . import views

urlpatterns = [
    # UI
    path("cargar/", views.cargar_horario, name="cargar_horario"),

    # APIs (selects encadenados)
    path("api/planes/",    views.api_planes_por_carrera, name="api_planes"),
    path("api/materias/",  views.api_materias_por_plan,  name="api_materias"),

    # API (time-slots por turno)
    path("api/timeslots/", views.api_timeslots_por_turno, name="api_timeslots"),

    # Guardar grilla
    path("api/guardar/",  views.horarios_guardar,        name="api_guardar"),
]
