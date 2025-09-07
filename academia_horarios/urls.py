from django.urls import path

from . import views

app_name = "academia_horarios"

urlpatterns = [
    # PÁGINA
    path("cargar/", views.cargar_horario, name="cargar_horario"),
    # APIs usadas por el JS:
    path("api/planes/", views.api_planes, name="api_planes"),
    path("api/materias/", views.api_materias, name="api_materias"),
    path("api/timeslots/", views.api_timeslots, name="api_timeslots"),
    path("api/guardar/", views.api_guardar, name="api_guardar"),
]
