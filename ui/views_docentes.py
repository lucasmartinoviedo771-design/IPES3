from django import forms
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from academia_core.models import Docente


class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        fields = ["apellido", "nombre", "dni", "email", "activo"]
        widgets = {
            "apellido": forms.TextInput(attrs={"class": "input", "placeholder": "Apellido"}),
            "nombre":   forms.TextInput(attrs={"class": "input", "placeholder": "Nombre"}),
            "dni":      forms.TextInput(attrs={"class": "input", "placeholder": "DNI"}),
            "email":    forms.EmailInput(attrs={"class": "input", "placeholder": "correo @ejemplo.com"}),
            "activo":   forms.CheckboxInput(attrs={}),
        }

    def clean_dni(self):
        dni = (self.cleaned_data.get("dni") or "").strip()
        if not dni.isdigit():
            raise forms.ValidationError("El DNI debe contener solo números.")
        return dni

@require_http_methods(["GET", "POST"])
def docente_nuevo(request):
    if request.method == "POST":
        form = DocenteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    docente = form.save()
                messages.success(request, f"Docente creado: {docente.apellido}, {docente.nombre}.")
                # Redirigimos a la pantalla donde lo vas a ver en el combo
                return redirect("/horarios/docente/")
            except IntegrityError:
                form.add_error("dni", "Ya existe un docente con ese DNI.")
    else:
        form = DocenteForm(initial={"activo": True})

    return render(request, "ui/docente_form.html", {"form": form})