# academia_horarios/management/commands/migrar_horarios.py
from django.core.management.base import BaseCommand
from django.db import transaction

from academia_horarios.models import Horario, HorarioClase

class Command(BaseCommand):
    help = "Migra datos del sistema de horarios antiguo (HorarioClase + TimeSlot) al nuevo modelo unificado (Horario)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Iniciando migración de horarios...")

        # Mapeo de día de la semana de número a código de 2 letras
        dia_map = {
            1: 'lu', 2: 'ma', 3: 'mi', 4: 'ju', 5: 'vi', 6: 'sa'
        }

        # Limpiar horarios existentes que podrían haber sido migrados antes para evitar duplicados
        # Esto hace que el script sea seguro de correr múltiples veces.
        # Una estrategia más compleja podría ser actualizar en lugar de borrar.
        # Por simplicidad y dado el contexto, un borrado y recarga es aceptable.
        # Horario.objects.all().delete()
        # self.stdout.write("Horarios existentes eliminados.")

        count = 0
        errores = 0
        
        # Iteramos sobre todos los HorarioClase existentes
        horarios_a_migrar = HorarioClase.objects.select_related(
            'comision__materia_en_plan__plan__profesorado',
            'comision__materia_en_plan__materia',
            'timeslot'
        ).prefetch_related('docentes')

        self.stdout.write(f"Se encontraron {horarios_a_migrar.count()} bloques de HorarioClase para migrar.")

        for hc in horarios_a_migrar:
            try:
                # Mapeo de campos
                dia_num = hc.timeslot.dia_semana
                if dia_num not in dia_map:
                    self.stderr.write(self.style.WARNING(f"Día de la semana inválido ({dia_num}) para HorarioClase ID {hc.id}. Omitiendo."))
                    errores += 1
                    continue

                dia_char = dia_map[dia_num]
                
                materia_en_plan = hc.comision.materia_en_plan
                espacio = materia_en_plan.materia
                plan = materia_en_plan.plan
                
                # El nuevo modelo Horario tiene una FK a un solo docente.
                # El viejo HorarioClase tiene un ManyToMany.
                # Como estrategia de migración, tomamos el primer docente asignado.
                docente_asignado = hc.docentes.first()

                # Crear la nueva entrada de Horario
                Horario.objects.create(
                    materia=espacio,
                    plan=plan,
                    profesorado=plan.profesorado,
                    anio=materia_en_plan.anio,
                    comision=hc.comision.nombre,
                    aula=hc.aula or "",
                    docente=docente_asignado,
                    dia=dia_char,
                    inicio=hc.timeslot.inicio,
                    fin=hc.timeslot.fin,
                    turno=hc.comision.turno,
                    # El campo cuatrimestral no tiene un mapeo directo, se asume False.
                    cuatrimestral=False 
                )
                count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error migrando HorarioClase ID {hc.id}: {e}"))
                errores += 1

        if errores > 0:
            self.stdout.write(self.style.WARNING(f"Migración completada con {errores} errores."))
        
        self.stdout.write(self.style.SUCCESS(f"Se migraron exitosamente {count} bloques de horario."))