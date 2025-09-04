from django.core.management.base import BaseCommand
from datetime import time
from academia_horarios.models import TimeSlot

class Command(BaseCommand):
    help = 'Seeds the TimeSlot table with initial data for the "manana" shift.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding TimeSlots...")

        def add(turno, dia, h1,m1, h2,m2, recreo=False):
            # Check if 'es_recreo' field exists
            has_recreo_field = "es_recreo" in [f.name for f in TimeSlot._meta.fields]
            
            defaults = {}
            if has_recreo_field:
                defaults["es_recreo"] = recreo

            obj, created = TimeSlot.objects.get_or_create(
                turno=turno, dia_semana=dia, inicio=time(h1,m1), fin=time(h2,m2),
                defaults=defaults
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'  + Created TimeSlot: {turno} {dia} {h1:02d}:{m1:02d}-{h2:02d}:{m2:02d}'))

        manana='manana'
        lu,ma,mi,ju,vi,sab = 1,2,3,4,5,6

        # Weekdays
        for d in (lu,ma,mi,ju,vi):
            add(manana,d,7,45,8,25)
            add(manana,d,8,25,9,5)
            add(manana,d,9,5,9,15, True)   # Recreo
            add(manana,d,9,15,9,55)
            add(manana,d,9,55,10,35)
            add(manana,d,10,35,10,45, True) # Recreo
            add(manana,d,10,45,11,25)
            add(manana,d,11,25,12,5)
            add(manana,d,12,5,12,45)

        # Saturday
        add(manana,sab,9,0,9,40)
        add(manana,sab,9,40,10,20)
        add(manana,sab,10,20,10,30, True)
        add(manana,sab,10,30,11,10)
        add(manana,sab,11,10,11,50)
        add(manana,sab,11,50,12,0, True)
        add(manana,sab,12,0,12,40)
        add(manana,sab,12,40,13,20)
        add(manana,sab,13,20,14,0)
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded TimeSlots.'))
