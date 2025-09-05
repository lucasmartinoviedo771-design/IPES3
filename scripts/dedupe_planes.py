from django.db.models import Count
from academia_core.models import PlanEstudios

# Detecta duplicados por (carrera, resolucion)
dups = (
    PlanEstudios.objects
    .values('carrera_id', 'resolucion')
    .annotate(n=Count('id'))
    .filter(n__gt=1)
)

total_borrados = 0
for d in dups:
    qs = (PlanEstudios.objects
          .filter(carrera_id=d['carrera_id'], resolucion=d['resolucion'])
          .order_by('id'))  # el primero es el "original" a mantener
    keep = qs.first()
    borrados = qs.exclude(id=keep.id).delete()[0]
    total_borrados += borrados
    print(f"✓ Mantengo Plan #{keep.id}  y borro {borrados} duplicado(s) para carrera={d['carrera_id']} resolucion={d['resolucion']}")

print("Listo. Total eliminados:", total_borrados)
print("Planes ahora:", PlanEstudios.objects.count())
