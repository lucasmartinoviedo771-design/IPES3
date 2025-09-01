# SEGUIMIENTO DEL PROYECTO — IPES2 (Sistema de Gestión Académica)

**Fecha de actualización:** 30/08/2025
**Repositorio:** `lucasmartinoviedo771-design/IPES2`
**Alcance:** Auditoría funcional/técnica del estado actual, correcciones, backlog priorizado, riesgos y plan de siguiente(s) iteración(es).

---

## 1) Resumen ejecutivo

El sistema IPES2 es una plataforma web basada en Django orientada a la gestión académica (estudiantes, inscripciones, planes, correlatividades, horarios, comisiones y docentes). En los últimos commits se evidencian avances significativos en **gestión de horarios**, validaciones de **topes de horas por materia**, **conflictos de docentes** y mejoras de **UX** en el panel de comisiones. También se corrigieron errores críticos (routing, importaciones y templates).

**Diagnóstico general:**

* **Funcionalidad core**: en buen estado y en consolidación.
* **Arquitectura y módulos**: correcta separación por apps, con oportunidades de estandarización.
* **Calidad**: faltan pruebas automatizadas amplias, linters/typing y pipeline CI/CD.
* **Seguridad/Operación**: reforzar gestión de `settings`, logging, manejo de secretos y endurecimiento de despliegue.

**Prioridad inmediata (P0):** hardening de `settings`, completar validaciones/errores en horarios, cobertura de pruebas de regresión, pipeline CI, checklist de release.

---

## 2) Mapa del sistema (alto nivel)

* **`academia_core`**: núcleo académico (estudiantes, cursos, inscripciones, calificaciones, planes, correlatividades).
* **`academia_horarios`**: horarios, comisiones, docentes, espacios.
* **Infraestructura/complementos**: `scripts/` de importación/exportación, `templates/`, `static/`, `ui/`, `requirements.txt`, `schema_erd.mmd` y `schema_models.md`.

> Recomendación: documentar un diagrama simple de arquitectura (cliente → vistas/panel → servicios/API → modelo/DB), y un **data dictionary** para las tablas principales.

---

## 3) Estado por fase (F0–F8)

> Semáforo: ✅ Completado · 🟡 En curso · 🔴 Pendiente

* **F0 Fundaciones** — 🟡
  **Evidencia**: estructura por apps, scripts de datos, esquemas.
  **Próx. pasos**: estandarizar `settings` por entorno; activar linters/typing; añadir CI.

* **F1 Horarios** — 🟡  (avance alto)
  **Evidencia**: `timeslots_api`, normalización día/turno, `ComisionDetailView → function view`, `HorarioInlineForm` con `clean/save`, validación de tope de horas y conflictos docentes, mejoras UX (chips, contador, botón deshabilitado).
  **Próx. pasos**: tests de regresión (form/validaciones/API); paginación y mensajes de error consistentes.

* **F2 Inscripción** — 🔴
  **Evidencia**: reglas de elegibilidad y correlatividades progresando; falta circuito E2E de inscripción (flujo completo con UI).
  **Próx. pasos**: endpoint(s)/vistas E2E; validaciones; pruebas de carga de datos.

* **F3 Comisiones** — 🟡
  **Evidencia**: detalle de comisión con formulario integrado; topes de horas.
  **Próx. pasos**: filtros/búsquedas; exportables; auditoría de integridad de datos.

* **F4 Docentes** — 🟡
  **Evidencia**: importación por DNI (184 registros), mejoras en modelo `Docente`.
  **Próx. pasos**: validaciones de duplicados/conflictos; edición masiva segura; permisos por rol.

* **F5 Notas** — 🔴
  **Evidencia**: no hay trazas del circuito de carga/consulta de notas.
  **Próx. pasos**: diseño de flujos y modelos; auditoría; UI básica + exportación.

* **F6 Paneles** — 🟡
  **Evidencia**: panel de comisiones en evolución.
  **Próx. pasos**: unificar estilo, manejo de estados vacíos/errores, accesibilidad (a11y).

* **F7 KPIs** — 🔴
  **Próx. pasos**: definir indicadores (inscripciones activas, ocupación de espacios, avance de plan, retención) y un panel mínimo (tabla/gráfico).

* **F8 Endurecimiento** — 🔴
  **Próx. pasos**: seguridad/ops (ver §6), performance (índices), backup/restore y checklist de release.

---

## 4) Cambios recientes clave (curado)

1. **Gestión de horarios**: `timeslots_api`, normalización de entradas, nuevo `HorarioInlineForm`, refactor de vista a función, URLs actualizadas.
2. **Tope de horas por materia**: campo `horas_catedra` y propiedades de cálculo en modelos; validación en `clean`.
3. **Conflictos de docentes**: validaciones en form + `m2m_changed` y `apps/__init__` para registrar señales.
4. **UX**: chips/contador de docentes seleccionados, ayuda de multiselección, deshabilitar “Agregar” al alcanzar tope, simplificación de errores en template.
5. **Importación de docentes**: script corregido y carga exitosa (184).
6. **Errores críticos resueltos**: rutas duplicadas, `SyntaxError`, `ImportError`, `NoReverseMatch`, `TemplateSyntaxError`, `AttributeError`.

> Sugerencia: mantener un **CHANGELOG.md** con formato semántico por versión (feat/fix/refactor/docs/chore) y enlaces a commits.

---

## 5) Errores/alertas detectados y propuestas de corrección

### 5.1 Diseño/Dominio

* **Enum/choices**: centralizar día/turno/bloques como `TextChoices`/`IntegerChoices` y mapear en base de datos; evita desalineaciones UI/BE.
* **Reglas de negocio en el modelo**: mantener `clean()` y `save()` con validaciones críticas (tope de horas, conflictos), y reforzar con **constraints** (UNIQUE/Check) a nivel DB.

### 5.2 Formularios y vistas

* **Form vs ModelForm**: si se mantiene `forms.Form`, asegurar persistencia atómica en `save()` y manejo de M2M; alternativamente, evaluar `ModelForm` + `inline formsets` para coherencia con Django Admin.
* **Mensajería de errores**: estandarizar formato (barra de alertas + inline), i18n y códigos de error reutilizables.

### 5.3 API/Integración

* Normalizar **nombres de rutas** y usar `reverse()` / `path()` con `name=`; evitar strings hardcodeados.
* Definir **contratos** de `timeslots_api` (entrada/salida JSON) y documentar con OpenAPI/`drf-spectacular` si se adopta DRF.

### 5.4 Datos

* **Importación Docentes**: validar encabezados/encoding; detectar duplicados por DNI + nombre; registrar bitácora (CSV de errores).
* **Correlatividades**: tests de consistencia (ciclos, prerequisitos imposibles) y utilitarios de reporte.

### 5.5 Seguridad/Operación

* Parametrizar **SECRET\_KEY/DB/ALLOWED\_HOSTS/DEBUG** vía entorno (`django-environ`).
* Activar **CSRF**, seguridad de cookies (`Secure`, `HttpOnly`, `SameSite`), `SECURE_*` en producción y redirección HTTPS.
* **Logging** estructurado a archivo/STDOUT con rotación y niveles por módulo; alertas de error (Sentry).
* Revisar exposición de **datos personales** (DNI, etc.) y **permisos** por rol (admin/docente/estudiante).
* Tareas de **backup/restore** + prueba de recuperación.

### 5.6 Calidad/DevEx

* Adoptar **pytest + pytest-django**, **factory\_boy/faker** y **coverage** (objetivo ≥70% en 2 iteraciones).
* Linters: **ruff** (PEP8/imports), **mypy** (typing gradual).
* Formato: **black** o ruff formatter.
* Pre-commit hooks.

---

## 6) Backlog priorizado (P0–P2)

**P0 (Crítico / próxima iteración)**

1. Hardening de `settings`: variables de entorno, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_*`.
2. Pruebas de regresión sobre horarios: `clean()`/`save()`, conflictos M2M, tope de horas, `timeslots_api`.
3. Pipeline **CI (GitHub Actions)**: instalar deps, ejecutar linters/typing/tests, publicar cobertura.
4. Bitácora de importación de docentes + validaciones (duplicados, formatos).
5. Checklist de release + documentación de despliegue (collectstatic, migraciones, superusuario, backup, rollback).

**P1 (Alto)**
6\. Flujo E2E de **inscripción** con UI, validaciones y pruebas.
7\. Paneles/KPIs mínimos: conteos de inscripciones, ocupación de aulas, horas asignadas vs tope.
8\. Indexación en DB (consultas por comisión, docente, día/turno, aula).
9\. Normalización de enums/choices y constraints en DB.
10\. Mejoras UX accesibilidad (a11y): foco, roles ARIA, contrastes, estados vacíos.

**P2 (Medio)**
11\. DRF + OpenAPI si se prevé consumo externo.
12\. Exportaciones (CSV/XLSX) de comisiones/horarios/notas.
13\. Internationalización (i18n) básico.
14\. Observabilidad (Sentry/Prometheus) y métricas técnicas (tiempo respuesta, errores 5xx).

---

## 7) Riesgos y mitigaciones

* **Regresiones en horarios**: elevar cobertura de tests, feature flags para cambios grandes.
* **Calidad de datos en importaciones**: validaciones estrictas y previsualización antes de aplicar.
* **Seguridad de datos personales**: revisión de permisos y enmascaramiento en logs; acuerdos legales según normativa local.
* **Despliegue manual**: CI/CD y checklist para evitar saltos de pasos.

---

## 8) Plan de pruebas (matriz resumida)

| Área            | Caso                 | Entrada                      | Resultado esperado                       |
| --------------- | -------------------- | ---------------------------- | ---------------------------------------- |
| Horarios        | Crear horario válido | Docente libre, bloque libre  | Alta exitosa                             |
| Horarios        | Tope de horas        | Supera tope en período       | Rechazo con mensaje específico           |
| Horarios        | Conflicto docente    | Mismo docente/bloque/período | Rechazo + hint de conflicto              |
| API Timeslots   | Filtrado             | día=Lu, turno=Mañana         | Lista consistente con enum/choices       |
| Import docentes | Duplicados           | DNI repetido                 | Se omite/agrupa y se reporta en bitácora |
| Permisos        | Acceso restringido   | Usuario sin rol              | 403/redirect                             |

> KPI de QA: tasa de éxito ≥95% en smoke suite; tiempo medio de corrección de bug P0 < 24h.

---

## 9) KPIs operativos (versión inicial)

* **Inscripciones activas** (por período).
* **Ocupación de aulas** (% por bloque/turno).
* **Horas cátedra asignadas vs tope** (por materia/comisión).
* **Tiempo de carga de docente/comisión**.
* **Errores 4xx/5xx** por día.

---

## 10) Checklist de release (prod)

1. `pytest` verde + cobertura publicada.
2. `ruff`/`mypy` sin errores.
3. Migraciones aplicadas y verificación de datos.
4. `collectstatic` OK; compresión/minificación.
5. `DEBUG=False`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` configurados.
6. Backup previo + plan de rollback.
7. Smoke tests post-deploy y monitoreo activado.

---

## 11) Anexos

### 11.1 Convenciones sugeridas

* **Ramas**: `main` (estable) · `dev` (integración) · `feature/*` (unidad de trabajo).
* **Commits**: Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`).
* **Versionado**: SemVer (`MAJOR.MINOR.PATCH`).

### 11.2 Plantillas útiles

* **Issue**: `As a <rol> I want <objetivo> so that <valor>`, criterios de aceptación, riesgos.
* **PR**: alcance, pruebas, impacto en datos, checklist.

---

> **Nota**: este seguimiento se basa en el repositorio y los últimos cambios observables. Cualquier diferencia con el estado real (p.ej. despliegue/infra) se ajustará tras una revisión conjunta del entorno y prioridades de negocio.
