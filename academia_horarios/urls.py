from django.urls import path

app_name = 'academia_horarios'

from .views import OfertaView, comision_detail, HorarioDeleteView, timeslots_api, cargar_horario, abrir_paralela, horarios_grilla, horarios_opciones, horarios_guardar

urlpatterns = [
    path("oferta/", OfertaView.as_view(), name="panel_oferta"),
    path("horarios/cargar/", cargar_horario, name="cargar_horario"),
    path("horarios/abrir-paralela/<int:plan_id>/<int:periodo_id>/", abrir_paralela, name="abrir_paralela"),
    path("comisiones/<int:pk>/", comision_detail, name="panel_comision"),
    path("horarios/<int:pk>/borrar/", HorarioDeleteView.as_view(), name="panel_horario_del"),
    path("horarios/api/timeslots/", timeslots_api, name="timeslots_api"),
    path("horarios/api/grilla/", horarios_grilla, name="horarios_grilla"),
    path("horarios/api/guardar/", horarios_guardar, name="api_guardar_horarios"),
    path("horarios/api/opciones/", horarios_opciones, name="horarios_opciones"),
    # New URLs for carrera administration
    path("administracion/carreras/", views.cargar_carrera_view, name="cargar_carrera"),
    path("administracion/carreras/api/get/<int:pk>/", views.carrera_get_api, name="carrera_get_api"),
    path("administracion/carreras/api/save/", views.carrera_save_api, name="carrera_save_api"),
    path("administracion/carreras/api/delete/<int:pk>/", views.carrera_delete_api, name="carrera_delete_api"),
]
