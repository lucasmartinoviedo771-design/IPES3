from django.urls import path

app_name = 'academia_horarios'

from .views import OfertaView, comision_detail, HorarioDeleteView, timeslots_api, cargar_horario, abrir_paralela

urlpatterns = [
    path("oferta/", OfertaView.as_view(), name="panel_oferta"),
    path("horarios/cargar/", cargar_horario, name="cargar_horario"),
    path("horarios/abrir-paralela/<int:plan_id>/<int:periodo_id>/", abrir_paralela, name="abrir_paralela"),
    path("comisiones/<int:pk>/", comision_detail, name="panel_comision"),
    path("horarios/<int:pk>/borrar/", HorarioDeleteView.as_view(), name="panel_horario_del"),
    path("horarios/api/timeslots/", timeslots_api, name="timeslots_api"),
]