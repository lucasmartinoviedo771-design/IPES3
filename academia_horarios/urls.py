from django.urls import path
from .views import ComisionDetailView
from . import views

urlpatterns = [
    # UI
    path("cargar/", views.cargar_horario, name="cargar_horario"),
    path("comisiones/<int:pk>/", ComisionDetailView.as_view(), name="comision_detail"),

    

    # API (time-slots por turno)
    path("api/timeslots/", views.api_timeslots_por_turno, name="api_timeslots"),

    # Guardar grilla
    path("api/guardar/",  views.horarios_guardar,        name="api_guardar"),
]
