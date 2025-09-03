from django.shortcuts import render
from academia_core.models import Profesorado

def horarios_profesorado(request):
    return render(request, "ui/horarios_profesorado.html", {
        "profesorados": Profesorado.objects.all().order_by("nombre")
    })

def horarios_docente(request):
    ctx = {
        "page_title": "Horarios por Docente",
    }
    return render(request, "ui/horarios_docente.html", ctx)
