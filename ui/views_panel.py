from django.shortcuts import render
from academia_core.models import Carrera

def horarios_profesorado(request):
    return render(request, "ui/horarios_profesorado.html", {
        "profesorados": Carrera.objects.all().order_by("nombre")
    })

def horarios_docente(request):
    ctx = {
        "page_title": "Horarios por Docente",
    }
    return render(request, "ui/horarios_docente.html", ctx)

from academia_horarios.models import Periodo

def gestionar_comisiones(request):
    ctx = {
        "page_title": "Gestionar Comisiones",
        "carreras": Carrera.objects.all().order_by("nombre"),
        "periodos": Periodo.objects.all().order_by("-ciclo_lectivo", "-cuatrimestre"),
    }
    return render(request, "ui/gestionar_comisiones.html", ctx)

