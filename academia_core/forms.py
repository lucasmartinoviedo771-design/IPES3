from django import forms
from .models import EstudianteProfesorado, InscripcionMateria, InscripcionMesa, Estudiante, Profesorado, PlanEstudios

class BaseStyledModelForm(forms.ModelForm):
    """Aplica clases del tema automáticamente (input/select/textarea/file)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            w = f.widget.__class__.__name__
            base = "input"
            if "Select" in w: base = "select"
            if "Textarea" in w: base = "textarea"
            if "FileInput" in w: base = "file"
            f.widget.attrs["class"] = (f.widget.attrs.get("class","") + " " + base).strip()

class InscripcionCarreraForm(BaseStyledModelForm):
    class Meta:
        model = EstudianteProfesorado
        fields = ["estudiante", "profesorado", "plan", "cohorte"]
        widgets = {
            "cohorte": forms.NumberInput(attrs={"min":2000, "max":2100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- DATA en combos ---
        self.fields['estudiante'].queryset  = Estudiante.objects.filter(activo=True).order_by('apellido','nombre')
        self.fields['profesorado'].queryset = Profesorado.objects.all().order_by('nombre')
        # Plan arranca vacío; lo carga AJAX:
        self.fields['plan'].queryset = PlanEstudios.objects.none()
        self.fields['plan'].empty_label = '---------'

class InscripcionMateriaForm(BaseStyledModelForm):
    class Meta:
        model = InscripcionMateria
        fields = ["estudiante", "materia", "comision", "estado"]
        widgets = {
            "comision": forms.TextInput(attrs={"placeholder":"A, B, C… (opcional)"}),
        }

class InscripcionMesaForm(BaseStyledModelForm):
    class Meta:
        model = InscripcionMesa
        fields = ["estudiante", "mesa", "condicion", "llamada", "estado"]