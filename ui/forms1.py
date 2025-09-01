from django import forms
from academia_core.models import PlanEstudios
from academia_horarios.models import Periodo

ANIOS = [('', '--')] + [(i, f'{i}°') for i in range(1, 6)]  # 1°..5°

class OfertaFilterForm(forms.Form):
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
        # Anchos cómodos sin romper el layout
        self.fields['plan'].widget.attrs.update({'style': 'min-width:28rem'})
        self.fields['anio'].widget.attrs.update({'style': 'min-width:10rem'})
        self.fields['periodo'].widget.attrs.update({'style': 'min-width:14rem'})
