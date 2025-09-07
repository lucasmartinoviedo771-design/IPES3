from django.contrib import messages
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.views.generic import CreateView

from .forms import InscripcionCarreraForm, InscripcionMateriaForm, InscripcionMesaForm


class BaseCreateView(CreateView):
    template_name = "inscripciones/form_base.html"
    page_title = ""
    submit_label = "Guardar"
    nav_blocks = {}  # qué items del menú dejar activos

    def get_success_url(self):
        # 1) si te pasan ?next=/ruta
        nxt = self.request.GET.get("next")
        if nxt:
            return nxt
        # 2) probá nombres conocidos de tu proyecto (ajustá la lista)
        for name in ["insc_carrera_list", "ui:estudiantes_list", "ui:dashboard", "dashboard"]:
            try:
                return reverse(name)
            except NoReverseMatch:
                continue
        # 3) fallback seguro
        return "/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.page_title
        ctx["submit_label"] = self.submit_label
        ctx.update(self.nav_blocks)
        return ctx

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"{self.page_title} registrada correctamente.")
        return resp


class InscripcionCarreraCreate(BaseCreateView):
    form_class = InscripcionCarreraForm
    template_name = "inscripciones/carrera.html"
    success_url = reverse_lazy("ui:dashboard")  # o tu listado

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(
            {
                "page_title": "Inscripción a Carrera",
                "submit_label": "Guardar Inscripción",
                "nav_insc": "active",
                "nav_insc_carrera": "active",
                # para el helper opcional:
                "success_url": str(self.success_url),
            }
        )
        return ctx


class InscripcionMateriaCreate(BaseCreateView):
    form_class = InscripcionMateriaForm
    page_title = "Inscripción a Materia"
    submit_label = "Guardar Inscripción"
    nav_blocks = {
        "nav_insc": "active",
        "nav_insc_materia": "active",
    }


class InscripcionMesaCreate(BaseCreateView):
    form_class = InscripcionMesaForm
    page_title = "Inscripción a Mesa"
    submit_label = "Guardar Inscripción"
    nav_blocks = {
        "nav_insc": "active",
        "nav_insc_mesa": "active",
    }
