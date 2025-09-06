from django.urls import path
from .views import (
    DashboardView,
    EstudianteListView, EstudianteDetailView, NuevoEstudianteView,
    DocenteListView, NuevoDocenteView,
    InscribirMateriaView, InscribirFinalView, InscripcionProfesoradoView,
    CartonEstudianteView, HistoricoEstudianteView,
    SwitchRoleView,
    CorrelatividadesView
)
from . import api
from . import views
from . import views_api
from . import views_panel

app_name = "ui"

from . import views_docentes

urlpatterns = [
    path("dashboard", DashboardView.as_view(), name="dashboard"),

    # Personas
    path("estudiantes/", EstudianteListView.as_view(), name="estudiantes_list"),
    path("estudiantes/<int:pk>", EstudianteDetailView.as_view(), name="estudiantes_detail"),
    path("personas/estudiantes/nuevo", NuevoEstudianteView.as_view(), name="estudiante_nuevo"),
    path("docentes", DocenteListView.as_view(), name="docentes_list"),
    path("personas/docentes/nuevo/", views_docentes.docente_nuevo, name="docente_nuevo"),

    # Inscripciones
    path("inscripciones/carrera", InscripcionProfesoradoView.as_view(), name="inscribir_carrera"),
    path("inscribir/materias", InscribirMateriaView.as_view(), name="inscribir_materias"),
    path("inscripciones/mesa-final", InscribirFinalView.as_view(), name="inscribir_final"),
    path("inscripciones/profesorado", InscripcionProfesoradoView.as_view(), name="inscripcion_profesorado"),

    path("inscripciones/carrera/nueva/", views.insc_carrera_new, name="insc_carrera_new"),
    path("inscripciones/materia/nueva/", views.insc_materia_new, name="insc_materia_new"),
    path("inscripciones/mesa/nueva/",    views.insc_mesa_new,    name="insc_mesa_new"),

    # Académico
    path("academico/correlatividades", CorrelatividadesView.as_view(), name="correlatividades"),

    # Cartón e Histórico del Estudiante
    path("estudiante/carton", CartonEstudianteView.as_view(), name="carton_estudiante"),
    path("estudiante/historico", HistoricoEstudianteView.as_view(), name="historico_estudiante"),

    # Cambiar rol
    path("cambiar-rol", SwitchRoleView.as_view(), name="switch_role"),

    # API Endpoints
    path("api/planes/", views_api.api_planes, name="api_planes"),
    path("api/materias/", views_api.api_materias, name="api_materias"),
    path("api/docentes/", views_api.api_docentes, name="api_docentes"),

    
    path("api/horario/save", views_api.api_horario_save, name="api_horario_save"),
    path("api/horarios/materia/", views_api.api_get_horarios_materia, name="api_get_horarios_materia"),
    path("api/comisiones/materia/", views_api.api_get_comisiones_materia, name="api_get_comisiones_materia"),
    path("api/comisiones/add/", views_api.api_add_comision, name="api_add_comision"),
    path("api/horarios/materia-plan", views_api.api_horarios_materia_plan, name="api_horarios_materia_plan"),
    
    path("api/turnos", views_api.api_turnos, name="api_turnos"),
    path("api/horarios-ocupados/", views_api.api_horarios_ocupados, name="api_horarios_ocupados"),
    path("api/cohortes", api.api_cohortes_por_plan, name="api_cohortes"),
    path("api/correlatividades", api.api_correlatividades_por_espacio, name="api_correlatividades_por_espacio"),
    path("api/materias-por-plan/", api.api_materias_por_plan, name="api_materias_por_plan"),
    path("api/calcular-estado-administrativo/", api.api_calcular_estado_administrativo, name="api_calcular_estado_administrativo"),

    

    # Oferta
    

    # Administracion
    path("administracion/comisiones/", views_panel.gestionar_comisiones, name="gestionar_comisiones"),

    # Horarios
    path("horarios/profesorado/", views_panel.horarios_profesorado, name="horarios_profesorado"),
    path("horarios/docente/", views_panel.horarios_docente, name="horarios_docente"),

    # APIs de solo-lectura para poblar las grillas
    path("api/carreras/", views_api.api_carreras, name="api_carreras"),
    path("api/horarios/profesorado", views_api.api_horarios_profesorado, name="api_horario_profesorado"),
    path("api/horarios/docente", views_api.api_horarios_docente, name="api_horario_docente"),
    path("api/grilla-config/", views_api.api_grilla_config, name="api_grilla_config"),
]