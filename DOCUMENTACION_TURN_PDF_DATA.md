# Inventario de datos para TurnPdfData

Este documento consolida el inventario de campos y dependencias relevantes para la construcción de `TurnPdfData`, a partir de la definición del modelo `Turns` y los esquemas de serialización existentes.

## 1. Modelo `Turns` en `app/models.py`

### Campos primarios y metadatos
- `id` (`UUID`): identificador primario del turno (`turn_id`).
- `reason` (`str | None`): motivo opcional asociado al turno.
- `state` (`TurnsState`): estado del turno (`waiting`, `finished`, `cancelled`, `rejected`, `accepted`).
- `date` (`date`): fecha programada del turno.
- `date_created` (`date`): fecha de creación.
- `date_limit` (`date`): fecha límite para confirmar o utilizar el turno.
- `time` (`time`): hora programada.

### Claves foráneas y relaciones
- `user_id` (`UUID | None`): referencia opcional a `users.user_id`. Relación `user: Optional[User]` (uno a muchos) que devuelve los datos completos del paciente asociado.【F:app/models.py†L288-L373】【F:app/models.py†L583-L611】
- `doctor_id` (`UUID | None`): referencia opcional a `doctors.doctor_id`. Relación `doctor: Optional[Doctors]` (uno a muchos) que permite acceder al profesional responsable.【F:app/models.py†L288-L373】【F:app/models.py†L611-L641】
- Relación muchos a muchos `services: List[Services]` mediante la tabla pivote `turns_services_link` (`TurnsServicesLink`). Cada servicio aporta nombre, descripción, precio e `id` propios.【F:app/models.py†L303-L359】【F:app/models.py†L498-L548】
- Relación muchos a muchos `schedules: List[MedicalSchedules]` a través de `turns_schedules_link` (`TurnsSchedulesLink`), con atributos `day`, `start_time`, `end_time`, `available` y `max_patients` en cada agenda médica vinculada.【F:app/models.py†L318-L368】【F:app/models.py†L548-L577】
- Relación uno a uno `appointment: Optional[Appointments]`, que enlaza con la cita clínica generada desde el turno cuando corresponde.【F:app/models.py†L347-L389】【F:app/models.py†L389-L430】

## 2. Serialización actual en `app/schemas/medica_area`

### Esquema base de turno (`turns.py`)
- `TurnsBase` replica los campos primarios (`id`, `reason`, `state`, `date`, `date_created`, `date_limit`, `time`) y las claves (`user_id`, `doctor_id`, `services`, `appointment_id`). La lista `services` se serializa como `List[UUID]` cuando se utiliza este esquema base.【F:app/schemas/medica_area/turns.py†L12-L33】
- `TurnsResponse` amplía `TurnsBase` exponiendo objetos anidados: `user: UserRead`, `doctor: DoctorResponse` y `service: List[ServiceResponse]` (nótese el nombre singular en el atributo, aunque representa una lista).【F:app/schemas/medica_area/turns.py†L45-L57】

### Esquemas auxiliares
- `UserRead` (importado desde `app.schemas`) aporta los datos básicos del paciente utilizados en respuestas API.【F:app/schemas/medica_area/turns.py†L9-L57】
- `DoctorResponse` incluye identificador (`id`), datos personales, indicadores de estado (`is_active`, `doctor_state`) y una colección opcional de agendas (`schedules: List[MedicalScheduleResponse]`).【F:app/schemas/medica_area/doctors.py†L8-L66】
- `ServiceResponse` agrega `id` y la relación anidada `specialty: SpecialtyResponse`, manteniendo nombre, descripción, precio e iconografía del servicio.【F:app/schemas/medica_area/services.py†L8-L42】
- `MedicalScheduleResponse` hereda `day`, `start_time`, `end_time` y suma `id` más una lista opcional de médicos (`doctors`).【F:app/schemas/medica_area/schedules.py†L8-L57】
- `AppointmentResponse` refleja datos de citas generadas a partir del turno, anidando `user`, `doctor`, `service` y `turn` completos cuando están disponibles.【F:app/schemas/medica_area/appointments.py†L8-L48】

## 3. Inventario propuesto para `TurnPdfData`

Para estructurar correctamente la información que debería consumir `TurnPdfData`, se recomienda contemplar los siguientes campos y formatos, alineados con los modelos y esquemas previos:

### Identificadores y estado del turno
- `turn_id` (`UUID`): identificador del turno.
- `appointment_id` (`UUID | None`): identificador de cita asociada (si existe).
- `state` (`str`): valor textual del `TurnsState` actual.
- `reason` (`str | None`): motivo del turno.

### Fechas y horarios
- `date` (`date`): fecha programada en formato ISO (`YYYY-MM-DD`).
- `time` (`time`): horario programado (`HH:MM:SS`).
- `date_created` (`date`): fecha de creación en formato ISO.
- `date_limit` (`date`): fecha límite informativa para el paciente.

### Datos del paciente (`user`)
- `user`: objeto con `id`, `username`, `first_name`, `last_name`, `dni`, `email`, `telephone`, `address`, `blood_type`, `url_image_profile`, según lo expuesto por `UserRead`.

### Datos del profesional (`doctor`)
- `doctor`: objeto que incluya `id`, `username`, `first_name`, `last_name`, `dni`, `email`, `telephone`, `speciality_id`, `doctor_state`, `schedules` (cada una con `day`, `start_time`, `end_time` e `id`).

### Servicios asociados
- `services`: lista de objetos con `id`, `name`, `description`, `price`, `icon_code`, `specialty` (incluyendo `id`, `name`, `description`).
- `price_total` (`float`): total calculado a partir de la suma de `service.price` (`Turns.price_total()`).【F:app/models.py†L347-L389】

### Agenda médica
- `schedules`: lista de agendas con `id`, `day`, `start_time`, `end_time`, `available`, `max_patients`.

### Cita derivada (`appointment`)
- `appointment`: objeto opcional con los campos de `AppointmentResponse`, particularmente útil para reflejar confirmaciones de atención.

### Metadatos adicionales sugeridos
- `generated_at` (`datetime`): timestamp de generación del PDF.
- `issuer` (`str`): origen o dependencia que emite el documento.

### Dependencias externas
- Catálogo de estados (`TurnsState`).
- Enumeración de días (`DayOfWeek`) para las agendas.
- Esquemas Pydantic utilizados en serialización (`UserRead`, `DoctorResponse`, `ServiceResponse`, `MedicalScheduleResponse`, `AppointmentResponse`).

Este inventario garantiza que `TurnPdfData` pueda reconstruir toda la información necesaria para generar un comprobante completo de turno, incluyendo paciente, profesional, servicios y agenda asociada, siguiendo los formatos ya establecidos en el dominio de turnos.
