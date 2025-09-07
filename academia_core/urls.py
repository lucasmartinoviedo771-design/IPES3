from django.urls import path

from .views import (
    cargar_carrera_view,
    carrera_delete_api,
    carrera_get_api,
    carrera_list_api,
    carrera_save_api,
    plan_list_api,
    plan_save_api,
)

app_name = "academia_core"

urlpatterns = [
    path("administracion/carreras/", cargar_carrera_view, name="cargar_carrera"),
    # APIs
    path("api/carreras/lista/", carrera_list_api, name="carrera_list_api"),
    path("api/carreras/get/<int:pk>/", carrera_get_api, name="carrera_get_api"),
    path("api/carreras/save/", carrera_save_api, name="carrera_save_api"),
    path("api/carreras/delete/<int:pk>/", carrera_delete_api, name="carrera_delete_api"),
    path("api/planes/lista/", plan_list_api, name="plan_list_api"),
    path("api/planes/guardar/", plan_save_api, name="plan_save_api"),
]
