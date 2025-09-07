from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from academia_core.models import (
    Carrera,
    Condicion,
    EspacioCurricular,
    Estudiante,
    EstudianteProfesorado,
    Materia,
    Movimiento,
    PlanEstudios,
)


class EstudianteProfesoradoModelTest(TestCase):
    def setUp(self):
        self.estudiante = Estudiante.objects.create(dni="12345678", apellido="Perez", nombre="Juan")
        self.carrera1 = Carrera.objects.create(nombre="Profesorado de Historia")
        self.carrera2 = Carrera.objects.create(nombre="Profesorado de Matemática")
        self.plan1_prof1 = PlanEstudios.objects.create(
            carrera=self.carrera1, resolucion="Res. 001/2020"
        )
        self.plan2_prof1 = PlanEstudios.objects.create(
            carrera=self.carrera1, resolucion="Res. 002/2020"
        )
        self.plan1_prof2 = PlanEstudios.objects.create(
            carrera=self.carrera2, resolucion="Res. 003/2020"
        )

    def test_clean_method_valid_plan(self):
        # Plan pertenece al profesorado
        inscripcion = EstudianteProfesorado(
            estudiante=self.estudiante,
            carrera=self.carrera1,
            plan=self.plan1_prof1,
            cohorte=2023,
        )
        try:
            inscripcion.full_clean()
        except ValidationError as e:
            self.fail(f"Validación falló inesperadamente: {e}")

    def test_clean_method_invalid_plan(self):
        # Plan no pertenece al profesorado
        inscripcion = EstudianteProfesorado(
            estudiante=self.estudiante,
            carrera=self.carrera1,
            plan=self.plan1_prof2,  # Plan de Profesorado2
            cohorte=2023,
        )
        with self.assertRaisesRegex(
            ValidationError, "El plan seleccionado no pertenece al profesorado."
        ):
            inscripcion.full_clean()

    def test_unique_estudiante_plan_constraint(self):
        # Crear una inscripción válida
        EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera1,
            plan=self.plan1_prof1,
            cohorte=2023,
        )
        # Intentar crear otra inscripción con el mismo estudiante y plan
        with self.assertRaises(ValidationError):
            EstudianteProfesorado.objects.create(
                estudiante=self.estudiante,
                carrera=self.carrera1,
                plan=self.plan1_prof1,
                cohorte=2024,  # Cohorte diferente, pero mismo estudiante y plan
            )

    def test_unique_estudiante_plan_different_plan(self):
        # Crear una inscripción válida
        EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera1,
            plan=self.plan1_prof1,
            cohorte=2023,
        )
        # Crear otra inscripción con el mismo estudiante pero diferente plan (del mismo profesorado)
        try:
            EstudianteProfesorado.objects.create(
                estudiante=self.estudiante,
                carrera=self.carrera1,
                plan=self.plan2_prof1,
                cohorte=2023,
            )
        except IntegrityError:
            self.fail("No debería haber fallado al crear inscripción con diferente plan.")


class EspacioCurricularModelTest(TestCase):
    def setUp(self):
        self.carrera = Carrera.objects.create(nombre="Profesorado de Historia")
        self.plan = PlanEstudios.objects.create(carrera=self.carrera, resolucion="Res. 001/2020")

    def test_unique_espacio_plan_nombre_constraint(self):
        materia = Materia.objects.create(nombre="Matemática I")
        EspacioCurricular.objects.create(
            plan=self.plan, materia=materia, anio="1°", cuatrimestre="1"
        )
        with self.assertRaises(IntegrityError):
            EspacioCurricular.objects.create(
                plan=self.plan,
                materia=materia,
                anio="1°",
                cuatrimestre="1",
            )


class MovimientoModelTest(TestCase):
    def setUp(self):
        self.estudiante = Estudiante.objects.create(dni="111", apellido="Doe", nombre="John")
        self.carrera = Carrera.objects.create(nombre="Profesorado de Prueba")
        self.plan = PlanEstudios.objects.create(carrera=self.carrera, resolucion="Res. Test")
        self.materia_test = Materia.objects.create(nombre="Materia Test")
        self.espacio = EspacioCurricular.objects.create(
            plan=self.plan, materia=self.materia_test, anio="1°", cuatrimestre="1"
        )
        self.condicion_regular, _ = Condicion.objects.get_or_create(
            codigo="REGULAR", defaults={"nombre": "Regular", "tipo": "REG"}
        )
        self.condicion_aprobado, _ = Condicion.objects.get_or_create(
            codigo="APROBADO", defaults={"nombre": "Aprobado", "tipo": "REG"}
        )
        self.condicion_final_aprobado, _ = Condicion.objects.get_or_create(
            codigo="FINAL_APROBADO", defaults={"nombre": "Aprobado Final", "tipo": "FIN"}
        )

    def test_clean_method_valid_movimiento(self):
        inscripcion = EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera,
            plan=self.plan,
            cohorte=2023,
            doc_dni_legalizado=True,
            doc_titulo_sec_legalizado=True,
            doc_cert_medico=True,
            doc_fotos_carnet=True,
            doc_folios_oficio=True,
            adeuda_materias=False,
        )
        movimiento = Movimiento(
            inscripcion=inscripcion,
            espacio=self.espacio,
            tipo="REG",
            fecha="2023-03-15",
            condicion=self.condicion_regular,
            nota_num=7.0,
        )
        try:
            movimiento.full_clean()
        except ValidationError as e:
            self.fail(f"Validación falló inesperadamente: {e}")

    def test_clean_method_invalid_nota_regular(self):
        inscripcion = EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera,
            plan=self.plan,
            cohorte=2023,
            doc_dni_legalizado=True,
            doc_titulo_sec_legalizado=True,
            doc_cert_medico=True,
            doc_fotos_carnet=True,
            doc_folios_oficio=True,
            adeuda_materias=False,
        )
        movimiento = Movimiento(
            inscripcion=inscripcion,
            espacio=self.espacio,
            tipo="REG",
            fecha="2023-03-15",
            condicion=self.condicion_regular,
            nota_num=11.0,  # Nota inválida
        )
        with self.assertRaisesRegex(
            ValidationError, "La nota de Regularidad debe estar entre 0 y 10."
        ):
            movimiento.full_clean()

    def test_clean_method_condicional_promocion(self):
        # Estudiante condicional no puede promocionar
        inscripcion = EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera,
            plan=self.plan,
            cohorte=2023,
            doc_dni_legalizado=True,
            doc_titulo_sec_legalizado=True,
            doc_cert_medico=True,
            doc_fotos_carnet=True,
            doc_folios_oficio=True,
            adeuda_materias=True,  # Set to True to make it condicional
        )
        # Corre la validación para que se derive legajo_completo/es_condicional
        inscripcion.full_clean()
        inscripcion.save()
        movimiento = Movimiento(
            inscripcion=inscripcion,
            espacio=self.espacio,
            tipo="REG",
            fecha="2023-03-15",
            condicion=self.condicion_aprobado,
            nota_num=8.0,
        )
        with self.assertRaisesRegex(
            ValidationError,
            "Estudiante condicional: no puede quedar Aprobado/Promoción por cursada.",
        ):
            movimiento.full_clean()

    def test_clean_method_final_nota_minima(self):
        # La prueba debe ejercitar la validación de "nota mínima" para FINAL,
        # no caer en un error previo por condición REGULAR.
        inscripcion = EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera,
            plan=self.plan,
            cohorte=2023,
            doc_dni_legalizado=True,
            doc_titulo_sec_legalizado=True,
            doc_cert_medico=True,
            doc_fotos_carnet=True,
            doc_folios_oficio=True,
            adeuda_materias=False,
        )
        # Asegura derivaciones antes de validar el movimiento
        inscripcion.full_clean()
        inscripcion.save()
        movimiento = Movimiento(
            inscripcion=inscripcion,
            espacio=self.espacio,
            tipo="FIN",
            fecha="2023-07-20",
            condicion=self.condicion_final_aprobado,
            nota_num=5.0,  # Nota menor a 6
        )
        with self.assertRaisesRegex(
            ValidationError, "Nota de Final por regularidad debe ser >= 6."
        ):
            movimiento.full_clean()

    def test_clean_method_espacio_profesorado_mismatch(self):
        otra_carrera = Carrera.objects.create(nombre="Otro Profesorado")
        otro_plan = PlanEstudios.objects.create(carrera=otra_carrera, resolucion="Res. Otro")
        otra_materia = Materia.objects.create(nombre="Otra Materia")
        otro_espacio = EspacioCurricular.objects.create(
            plan=otro_plan, materia=otra_materia, anio="1°", cuatrimestre="1"
        )
        inscripcion = EstudianteProfesorado.objects.create(
            estudiante=self.estudiante,
            carrera=self.carrera,
            plan=self.plan,
            cohorte=2023,
            doc_dni_legalizado=True,
            doc_titulo_sec_legalizado=True,
            doc_cert_medico=True,
            doc_fotos_carnet=True,
            doc_folios_oficio=True,
            adeuda_materias=False,
        )
        movimiento = Movimiento(
            inscripcion=inscripcion,
            espacio=otro_espacio,
            tipo="REG",
            fecha="2023-03-15",
            condicion=self.condicion_regular,
            nota_num=7.0,
        )
        with self.assertRaisesRegex(
            ValidationError,
            "El espacio no pertenece al mismo profesorado de la inscripción del estudiante.",
        ):
            movimiento.full_clean()


class PanelViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")

    def test_panel_view_for_student(self):
        student = Estudiante.objects.create(dni="test_student", apellido="Test", nombre="Student")
        profile = self.user.perfil
        profile.rol = "ESTUDIANTE"
        profile.estudiante = student
        profile.save()

        student_group, _ = Group.objects.get_or_create(name="Estudiante")
        self.user.groups.add(student_group)

        # The view uses request.session['active_role']
        session = self.client.session
        session["active_role"] = "Estudiante"
        session.save()

        response = self.client.get(reverse("ui:dashboard"))
        self.assertRedirects(response, reverse("ui:carton_estudiante"))

        response = self.client.get(reverse("ui:carton_estudiante"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ui/estudiante/carton.html")

    def test_panel_correlatividades_view(self):
        secretaria_group, _ = Group.objects.get_or_create(name="Secretaría")
        self.user.groups.add(secretaria_group)

        # The view uses request.session['active_role']
        session = self.client.session
        session["active_role"] = "Secretaría"
        session.save()

        response = self.client.get(reverse("ui:correlatividades"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ui/planes/correlatividades_form.html")

    def test_panel_horarios_view(self):
        response = self.client.get(reverse("ui:horarios_profesorado"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ui/horarios_profesorado.html")

    def test_panel_docente_view(self):
        # Asignar el rol de docente al usuario
        docente_group = Group.objects.create(name="Docente")
        self.user.groups.add(docente_group)

        response = self.client.get(reverse("ui:docentes_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ui/personas/docentes_list.html")
