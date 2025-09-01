# ui/forms.py
from django import forms
from academia_core.models import PlanEstudios, Estudiante, Docente, EstudianteProfesorado
from academia_horarios.models import Periodo

class UIFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            
            base_class = "select" if isinstance(field.widget, forms.Select) else "input"
            
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " " + base_class).strip()

# --- Formulario de filtro para la oferta académica ---
ANIOS = [('', '--')] + [(i, f'{i}°') for i in range(1, 6)]  # 1°..5°

class OfertaFilterForm(UIFormMixin, forms.Form):
    plan = forms.ModelChoiceField(
        queryset=PlanEstudios.objects.select_related('profesorado').order_by(
            'profesorado__nombre', 'resolucion'
        ),
        label="Plan",
        empty_label=None,
        required=True,
    )
    anio = forms.ChoiceField(
        choices=ANIOS,
        label="Año",
        required=False,
    )
    periodo = forms.ModelChoiceField(
        queryset=Periodo.objects.order_by('-ciclo_lectivo', '-cuatrimestre'),
        label="Período",
        required=False,
        empty_label="--",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Anchos para un layout prolijo
        self.fields['plan'].widget.attrs.update({'style': 'min-width:28rem'})
        self.fields['anio'].widget.attrs.update({'style': 'min-width:10rem'})
        self.fields['periodo'].widget.attrs.update({'style': 'min-width:14rem'})

# --- Formularios simples para Estudiantes/Docentes (ModelForm básico) ---
class EstudianteNuevoForm(UIFormMixin, forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = "__all__"

class EstudianteEditarForm(EstudianteNuevoForm):
    pass

class NuevoDocenteForm(UIFormMixin, forms.ModelForm):
    class Meta:
        model = Docente
        fields = "__all__"

class DocenteEditarForm(NuevoDocenteForm):
    pass

# --- Constantes que importan algunas views ---
CERT_DOCENTE_LABEL = "Certificado de trabajo docente (opcional)"

# --- Placeholders no funcionales (solo para que el import no rompa) ---
class EstudianteMatricularForm(UIFormMixin, forms.Form):
    """Pendiente de implementar."""
    pass

class InscripcionProfesoradoForm(UIFormMixin, forms.ModelForm):
    """Pendiente: CreateView real. Dejo helpers para que no explote."""
    class Meta:
        model = EstudianteProfesorado
        exclude = ['legajo_estado', 'condicion_admin', 'promedio_general']

    def compute_estado_admin(self):
        return None
    def _calculate_estado_from_data(self, *args, **kwargs):
        return None

class CorrelatividadesForm(UIFormMixin, forms.Form):
    """Pendiente de implementar."""
    pass
