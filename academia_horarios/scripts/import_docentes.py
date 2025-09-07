import json
import os

from django.db import transaction

from academia_horarios.models import Docente

# Usar una ruta relativa desde la raíz del proyecto
file_path = os.path.join("academia_horarios", "fixtures", "seed_docentes_desde_pdf.json")

creados = 0
actualizados = 0
repetidos = 0
visto = set()

print(f"Importando desde {file_path}...")

try:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: El archivo no se encontró en {file_path}")
    exit()
except json.JSONDecodeError:
    print(f"Error: El archivo {file_path} no es un JSON válido.")
    exit()

with transaction.atomic():
    for obj in data:
        fields = obj.get("fields", obj)
        dni = (fields.get("dni") or "").strip()
        nombre = (fields.get("apellido_nombre") or "").strip()

        if not nombre:
            continue

        if dni:
            if dni in visto:
                repetidos += 1
                continue
            visto.add(dni)
            doc, created = Docente.objects.update_or_create(
                dni=dni, defaults={"apellido_nombre": nombre}
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        else:
            # Sin DNI, deduplicar por nombre exacto
            doc, created = Docente.objects.get_or_create(apellido_nombre=nombre)
            if created:
                creados += 1
            else:
                actualizados += 1

print(f"Creados: {creados} | Actualizados: {actualizados} | Repetidos en archivo: {repetidos}")
