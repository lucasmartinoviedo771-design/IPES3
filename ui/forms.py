# ui/forms.py
from django import forms
from django.apps import apps

PlanEstudios = apps.get_model('academia_core', 'PlanEstudios')
Estudiante = apps.get_model('academia_core', 'Estudiante')
Docente = apps.get_model('academia_core', 'Docente')
EstudianteProfesorado = apps.get_model('academia_core', 'EstudianteProfesorado')
Periodo = apps.get_model('academia_horarios', 'Periodo')

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
        queryset=PlanEstudios.objects.select_related('carrera').order_by(
            'carrera__nombre', 'resolucion'
        ),
        required=False,
        empty_label='Todos los planes',
        label='Plan de estudios',
    )

    periodo = forms.ModelChoiceField(
        queryset=Periodo.objects.all().order_by('-id'),  # orden seguro
        required=False,
        empty_label='Último',
        label='Período',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si en tu versión original seteabas estilos:
        if 'periodo' in self.fields:
            self.fields['periodo'].widget.attrs.update({'style': 'min-width:14rem'})
        if 'plan' in self.fields:
            self.fields['plan'].widget.attrs.update({'style': 'min-width:18rem'})

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
