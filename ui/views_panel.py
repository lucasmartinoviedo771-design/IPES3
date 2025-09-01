from django.shortcuts import render

def horarios_profesorado(request):
    # Estos combos se llenan por JS usando tus endpoints ya existentes:
    # ui:api_planes, ui:api_materias, ui:api_docentes (si necesitás filtro)
    ctx = {
        "page_title": "Horarios por Profesorado",
    }
    return render(request, "ui/horarios_profesorado.html", ctx)

def horarios_docente(request):
    ctx = {
        "page_title": "Horarios por Docente",
    }
    return render(request, "ui/horarios_docente.html", ctx)
