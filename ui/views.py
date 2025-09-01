# ui/views.py
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    CreateView,
    FormView,
    TemplateView,
    ListView,
    DetailView,
)
from django.shortcuts import redirect, get_object_or_404, render
from django.db.models import Q
from django.views import View
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db import transaction
from django.apps import apps
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

# Modelos
from academia_core.models import Estudiante, Docente
from academia_horarios.models import Comision, TimeSlot, HorarioClase
from academia_horarios import services

# Formularios de la app UI
from .forms import (
    EstudianteNuevoForm,
    InscripcionProfesoradoForm,
    NuevoDocenteForm,
    CERT_DOCENTE_LABEL,
    CorrelatividadesForm,
    OfertaFilterForm,
)

# Mixin de permisos por rol
from .permissions import RolesPermitidosMixin, RolesAllowedMixin
from .auth_views import ROLE_HOME # Importar ROLE_HOME

def resolve_estudiante_from_request(request):
    """
    Devuelve un Estudiante o None.
    - Si el usuario logueado es Estudiante -> su registro.
    - Si llega ?est=<ID> -> ese registro (si existe).
    """
    user = request.user
    if hasattr(user, "estudiante"):
        return user.estudiante

    est_id = request.GET.get("est")
    if est_id:
        try:
            return Estudiante.objects.get(pk=est_id)
        except Estudiante.DoesNotExist:
            return None
    return None


# ---------- Dashboard ----------
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "ui/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        role = request.session.get("active_role")
        if role and role.lower().startswith("estudiante"):
            try:
                return redirect(reverse("ui:carton_estudiante"))
            except Exception:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, "userprofile", None)
        ctx["current_role"] = getattr(profile, "rol", "") or ""
        ctx["current_user"] = self.request.user
        return ctx


# ---------- Vistas de Personas (Estudiantes y Docentes) ----------
class EstudianteListView(LoginRequiredMixin, ListView):
    model = Estudiante
    template_name = "ui/personas/estudiantes_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by("apellido", "nombre")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(apellido__icontains=q) | Q(nombre__icontains=q) |
                Q(dni__icontains=q) | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx

class EstudianteDetailView(LoginRequiredMixin, DetailView):
    model = Estudiante
    template_name = "ui/personas/estudiantes_detail.html"
    context_object_name = "obj"

class NuevoEstudianteView(LoginRequiredMixin, RolesAllowedMixin, CreateView):
    permission_required = "academia_core.add_estudiante"
    allowed_roles = ["Bedel", "Secretaría", "Admin"]
    form_class = EstudianteNuevoForm
    template_name = "ui/personas/estudiante_form.html"
    success_url = reverse_lazy("ui:estudiante_nuevo")

class DocenteListView(LoginRequiredMixin, ListView):
    model = Docente
    template_name = "ui/personas/docentes_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by("apellido", "nombre")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(apellido__icontains=q) | Q(nombre__icontains=q) |
                Q(dni__icontains=q) | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx

class NuevoDocenteView(LoginRequiredMixin, RolesAllowedMixin, CreateView):
    permission_required = "academia_core.add_docente"
    allowed_roles = ["Secretaría", "Admin"]
    form_class = NuevoDocenteForm
    template_name = "ui/personas/docente_form.html"
    success_url = reverse_lazy("ui:docente_nuevo")


# ---------- Vistas de Inscripciones ----------
class InscribirCarreraView(LoginRequiredMixin, RolesAllowedMixin, TemplateView):
    """
    Pantalla de Inscripción a Carrera (placeholder).
    Restringida a Secretaría / Admin / Bedel.
    """
    allowed_roles = ["Secretaría", "Admin", "Bedel"]
    permission_required = "academia_core.add_estudianteprofesorado"
    template_name = "ui/inscripciones/carrera.html"
    extra_context = {"page_title": "Inscribir a Carrera"}

class InscribirMateriaView(LoginRequiredMixin, RolesAllowedMixin, TemplateView):
    template_name = "ui/inscripciones/materia.html"
    allowed_roles = ["Admin", "Secretaría", "Bedel", "Docente", "Estudiante"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prefill_est"] = self.request.GET.get("est") or ""
        ctx["estudiantes"] = Estudiante.objects.all().order_by("apellido", "nombre").values("id", "apellido", "nombre", "dni")
        return ctx

class InscribirFinalView(LoginRequiredMixin, RolesAllowedMixin, TemplateView):
    allowed_roles = ["Secretaría", "Admin", "Bedel"]
    permission_required = "academia_core.enroll_others"
    template_name = "ui/inscripciones/final.html"
    extra_context = {"page_title": "Inscribir a Mesa de Final"}

class InscripcionProfesoradoView(RolesPermitidosMixin, LoginRequiredMixin, CreateView):
    allowed_roles = {"Admin", "Secretaría", "Bedel"}
    template_name = "ui/inscripciones/inscripcion_profesorado_form.html"
    form_class = InscripcionProfesoradoForm
    success_url = reverse_lazy("ui:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if est := self.request.GET.get("est"):
            kwargs["initial_estudiante"] = est
        return kwargs

    def form_valid(self, form):
        obj = form.save()
        cd = form.cleaned_data
        RequisitosIngreso = apps.get_model("academia_core", "RequisitosIngreso")
        req_fields = [
            "req_dni", "req_cert_med", "req_fotos", "req_folios",
            "req_titulo_sec", "req_titulo_tramite", "req_adeuda",
            "req_adeuda_mats", "req_adeuda_inst", "req_titulo_sup",
            "req_incumbencias", "req_condicion",
        ]
        RequisitosIngreso.objects.update_or_create(
            inscripcion=obj,
            defaults={k: cd.get(k) for k in req_fields}
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        estado, is_cert = None, False
        if form:
            if form.is_bound and form.is_valid():
                estado, is_cert = form.compute_estado_admin()
            elif not form.is_bound and form.initial:
                estado, is_cert = form._calculate_estado_from_data(form.initial)
        ctx.update({
            "estado_admin": estado,
            "is_cert_docente": is_cert,
            "CERT_DOCENTE_LABEL": CERT_DOCENTE_LABEL,
        })
        return ctx


# ---------- Vistas Académicas ----------
class CorrelatividadesView(LoginRequiredMixin, RolesAllowedMixin, FormView):
    allowed_roles = {"Secretaría", "Admin"}
    template_name = "ui/planes/correlatividades_form.html"
    form_class = CorrelatividadesForm
    success_url = reverse_lazy("ui:correlatividades")

    APP_LABEL = "academia_core"
    CORR_MODEL = "Correlatividad"
    TIPO_CURSAR = "CURSAR"
    REQUISITO_REGULAR = "REGULARIZADA"
    REQUISITO_APROBADA = "APROBADA"

    def form_valid(self, form):
        Correlatividad = apps.get_model(self.APP_LABEL, self.CORR_MODEL)
        cd = form.cleaned_data
        plan, espacio = cd["plan"], cd["espacio"]
        reg_ids = [int(x) for x in (cd["correlativas_regular"] or [])]
        apr_ids = [int(x) for x in (cd["correlativas_aprobada"] or [])]

        try:
            with transaction.atomic():
                Correlatividad.objects.filter(plan=plan, espacio=espacio).delete()
                for rid in reg_ids:
                    Correlatividad.objects.create(
                        plan=plan, espacio=espacio, requiere_espacio_id=rid,
                        tipo=self.TIPO_CURSAR, requisito=self.REQUISITO_REGULAR
                    )
                for aid in apr_ids:
                    Correlatividad.objects.create(
                        plan=plan, espacio=espacio, requiere_espacio_id=aid,
                        tipo=self.TIPO_CURSAR, requisito=self.REQUISITO_APROBADA
                    )
            messages.success(self.request, "Correlatividades guardadas correctamente.")
        except LookupError:
            messages.error(self.request, "Modelo de correlatividades no encontrado.")
        return super().form_valid(form)


# --- Vistas del Estudiante ---
class CartonEstudianteView(LoginRequiredMixin, RolesAllowedMixin, TemplateView):
    template_name = "ui/estudiante/carton.html"
    allowed_roles = ["Estudiante", "Bedel", "Secretaría", "Admin"]

class HistoricoEstudianteView(LoginRequiredMixin, RolesAllowedMixin, TemplateView):
    template_name = "ui/estudiante/historico.html"
    allowed_roles = ["Estudiante", "Bedel", "Secretaría", "Admin"]


# --- Vista para cambiar de rol ---
class SwitchRoleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        new_role = request.POST.get("role")
        allowed = set(request.user.groups.values_list("name", flat=True))
        if request.user.is_superuser:
            allowed.add("Admin")
        if new_role not in allowed:
            return HttpResponseForbidden("No tenés ese rol.")
        request.session["active_role"] = new_role
        return redirect(reverse(ROLE_HOME.get(new_role, "ui:dashboard")))


# --- Vistas para Comisiones (agregadas) ---
def _redir_comision(comision):
    """
    Cambiá este redirect al name real de tu detalle de comisión.
    Si ya tenés una vista llamada 'comision_detail' namespaced en ui, dejá como está.
    """
    return redirect("ui:comision_detail", pk=comision.pk)

@require_POST
def asignar_docente(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    docente_id = request.POST.get("docente_id")
    if not docente_id:
        messages.error(request, "Debés elegir un docente.")
        return _redir_comision(comision)

    docente = get_object_or_404(Docente, pk=docente_id)
    try:
        services.asignar_docente_a_comision(comision, docente)
        messages.success(request, "Docente asignado con éxito.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))
    return _redir_comision(comision)

@require_POST
def agregar_horario(request, pk):
    """
    Crea (o reutiliza) un TimeSlot y agrega un HorarioClase a la comisión.
    Valida con HorarioClase.clean(): bloque ocupado, tope HC, y conflicto docente.
    """
    comision = get_object_or_404(Comision, pk=pk)

    try:
        dia_semana = int(request.POST.get("dia_semana"))
        inicio = request.POST.get("inicio")  # "HH:MM"
        fin = request.POST.get("fin")        # "HH:MM"
    except Exception:
        messages.error(request, "Datos de horario inválidos.")
        return _redir_comision(comision)

    docente_id = request.POST.get("docente_id") or None
    aula = (request.POST.get("aula") or "").strip()

    ts, _ = TimeSlot.objects.get_or_create(dia_semana=dia_semana, inicio=inicio, fin=fin)

    hc = HorarioClase(comision=comision, timeslot=ts, aula=aula)
    if docente_id:
        hc.docente = get_object_or_404(Docente, pk=docente_id)

    try:
        hc.full_clean()  # dispara tu clean() con todas las validaciones
        hc.save()
        messages.success(request, "Horario agregado correctamente.")
    except ValidationError as e:
        # juntar errores amigables
        if hasattr(e, "message_dict"):
            msgs = []
            for field, errs in e.message_dict.items():
                for err in errs:
                    msgs.append(f"{field}: {err}")
            messages.error(request, " • ".join(msgs))
        else:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
    return _redir_comision(comision)

def oferta_por_plan(request):
    form = OfertaFilterForm(request.GET or None)

    # Si necesitás filtrar Período según algo, podés retocar el queryset acá.
    # Por ejemplo, siempre aseguramos que tenga periodos:
    form.fields['periodo'].queryset = form.fields['periodo'].queryset

    ctx = {
        'form': form,
        # ... y lo que ya usás para construir la tabla / resultados
    }
    return render(request, 'ui/oferta_por_plan.html', ctx)