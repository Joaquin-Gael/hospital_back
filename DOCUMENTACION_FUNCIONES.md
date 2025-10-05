# 📚 Documentación de Funciones - Sistema Hospitalario

## Índice
- [1. Funciones Principales (main.py)](#1-funciones-principales-mainpy)
- [2. API de Usuarios (users.py)](#2-api-de-usuarios-userspy)
- [3. API de Autenticación (auth.py)](#3-api-de-autenticación-authpy)
- [4. API del Área Médica (medic_area.py)](#4-api-del-área-médica-medic_areapy)
- [5. API de Cajas (cashes.py)](#5-api-de-cajas-cashespy)
- [6. API del Asistente IA (ai_assistant.py)](#6-api-del-asistente-ia-ai_assistantpy)
- [7. Core - Autenticación (core/auth.py)](#7-core---autenticación-coreauthpy)
- [8. Core - Base de Datos (db/main.py)](#8-core---base-de-datos-dbmainpy)
- [9. Modelos de Datos (models.py)](#9-modelos-de-datos-modelspy)

---

## 1. Funciones Principales (main.py)

### `lifespan(app: FastAPI)`
**Descripción**: Gestiona el ciclo de vida de la aplicación FastAPI.
- **Tipo**: Context Manager Asíncrono
- **Funcionalidad**: 
  - Inicializa la base de datos
  - Ejecuta migraciones
  - Configura usuario administrador
  - Crea tablas de almacenamiento
  - Limpia recursos al cerrar (en modo debug)
- **Uso**: Automático al iniciar/cerrar la aplicación

### `health_check()`
**Descripción**: Endpoint de verificación de salud del sistema.
- **Método HTTP**: GET
- **Ruta**: `/_health_check/`
- **Retorna**: Estado y tiempo de respuesta de la base de datos
- **Uso**: Monitoreo del sistema

### `scalar_html()`
**Descripción**: Sirve la documentación interactiva Scalar (solo en modo debug).
- **Método HTTP**: GET
- **Ruta**: `/scalar`
- **Funcionalidad**: Interfaz moderna para documentación de API
- **Condición**: Solo disponible cuando `debug=True`

### `get_secret()`
**Descripción**: Obtiene el prefijo secreto de la API.
- **Método HTTP**: GET
- **Ruta**: `/id_prefix_api_secret/`
- **Retorna**: ID del prefijo de la API
- **Uso**: Configuración de clientes

### `websocket_endpoint(websocket: WebSocket, secret: str)`
**Descripción**: Endpoint WebSocket para comunicación en tiempo real.
- **Protocolo**: WebSocket
- **Ruta**: `/{secret}/ws`
- **Funcionalidad**: 
  - Acepta conexiones WebSocket
  - Envía mensaje de bienvenida
  - Hace eco de mensajes recibidos
- **Manejo de errores**: Captura desconexiones y errores

### Clases de Archivos Estáticos

#### `SPAStaticFiles`
**Descripción**: Maneja archivos estáticos para Single Page Applications.
- **Hereda de**: StaticFiles
- **Funcionalidad**: 
  - Sirve archivos estáticos del frontend
  - Redirige rutas no encontradas al index.html
  - Evita conflictos con rutas de API

#### `AdminSPAStaticFiles`
**Descripción**: Versión específica para el panel de administración.
- **Funcionalidad similar** a SPAStaticFiles pero para rutas `/admin`

---

## 2. API de Usuarios (users.py)

### Funciones de Consulta

#### `get_users(session: SessionDep)`
**Descripción**: Obtiene lista de todos los usuarios del sistema.
- **Método HTTP**: GET
- **Ruta**: `/users/`
- **Autenticación**: Requerida
- **Retorna**: Lista de usuarios con información completa
- **Campos incluidos**: ID, estado, rol, información personal, seguros médicos

#### `get_user_by_id(session: SessionDep, user_id: UUID)`
**Descripción**: Obtiene un usuario específico por su ID.
- **Método HTTP**: GET
- **Ruta**: `/users/{user_id}/`
- **Autenticación**: Requerida
- **Parámetros**: `user_id` - UUID del usuario
- **Retorna**: Información completa del usuario
- **Error**: 404 si no se encuentra

#### `me_user(request: Request, session: SessionDep)`
**Descripción**: Obtiene información del usuario autenticado.
- **Método HTTP**: GET
- **Ruta**: `/users/me`
- **Autenticación**: Requerida
- **Retorna**: Perfil del usuario actual
- **Funcionalidad**: Actualiza sesión y refresca datos

### Funciones de Creación y Registro

#### `add_user(session: SessionDep, user: UserCreate)`
**Descripción**: Registra un nuevo usuario en el sistema.
- **Método HTTP**: POST
- **Ruta**: `/users/add/`
- **Autenticación**: No requerida (registro público)
- **Funcionalidad**:
  - Crea usuario con datos del formulario
  - Hashea la contraseña
  - Guarda imagen de perfil (opcional)
  - Valida datos de entrada
- **Retorna**: Usuario creado con información básica

### Funciones de Actualización

#### `update_user(request: Request, user_id: UUID, session: SessionDep, user_form: UserUpdate)`
**Descripción**: Actualiza información de un usuario existente.
- **Método HTTP**: PATCH
- **Ruta**: `/users/update/{user_id}/`
- **Autenticación**: Requerida (propietario o superusuario)
- **Funcionalidad**:
  - Actualiza campos específicos
  - Maneja seguros médicos
  - Actualiza imagen de perfil
  - Valida permisos de edición

#### `update_user_password(request: Request, user_id: UUID, session: SessionDep, user_form: UserPasswordUpdate)`
**Descripción**: Cambia la contraseña de un usuario.
- **Método HTTP**: PATCH
- **Ruta**: `/users/update/{user_id}/password`
- **Autenticación**: Requerida
- **Validaciones**:
  - Verifica contraseña actual
  - Confirma nueva contraseña
  - Envía notificación por email
- **Seguridad**: Hashea nueva contraseña

### Funciones de Recuperación de Contraseña

#### `update_petition_password(session: SessionDep, data: UserPetitionPasswordUpdate)`
**Descripción**: Inicia proceso de recuperación de contraseña.
- **Método HTTP**: POST
- **Ruta**: `/users/update/petition/password`
- **Funcionalidad**:
  - Genera código de recuperación aleatorio
  - Almacena código temporalmente
  - Envía email con código
- **Seguridad**: Código de 6 caracteres alfanuméricos

#### `verify_code(session: SessionDep, email: str, code: str)`
**Descripción**: Verifica el código de recuperación.
- **Método HTTP**: POST
- **Ruta**: `/users/update/verify/code`
- **Validaciones**:
  - Verifica existencia del usuario
  - Valida código y expiración
  - Marca código como verificado

#### `update_confirm_password(session: SessionDep, email: str, code: str, new_password: str)`
**Descripción**: Confirma cambio de contraseña con código verificado.
- **Método HTTP**: POST
- **Ruta**: `/users/update/confirm/password`
- **Funcionalidad**:
  - Valida código verificado
  - Actualiza contraseña
  - Envía confirmación por email

### Funciones de Eliminación y Moderación

#### `delete_user(request: Request, user_id: UUID, session: SessionDep)`
**Descripción**: Elimina un usuario del sistema.
- **Método HTTP**: DELETE
- **Ruta**: `/users/delete/{user_id}/`
- **Autenticación**: Solo superusuarios
- **Restricción**: No puede eliminar su propio usuario
- **Retorna**: Confirmación de eliminación

#### `ban_user(request: Request, user_id: UUID, session: SessionDep)`
**Descripción**: Banea (desactiva) un usuario.
- **Método HTTP**: PATCH
- **Ruta**: `/users/ban/{user_id}/`
- **Autenticación**: Solo superusuarios
- **Funcionalidad**: Cambia estado activo del usuario

#### `unban_user(request: Request, user_id: UUID, session: SessionDep)`
**Descripción**: Desbanea (reactiva) un usuario.
- **Método HTTP**: PATCH
- **Ruta**: `/users/unban/{user_id}/`
- **Autenticación**: Solo superusuarios
- **Funcionalidad**: Restaura estado activo del usuario

### Funciones de Verificación de Documentos

#### `verify_dni(dni_form: DniForm)`
**Descripción**: Extrae número de DNI de imágenes usando OCR.
- **Método HTTP**: POST
- **Ruta**: `/users/verify/dni`
- **Autenticación**: Requerida
- **Funcionalidad**:
  - Acepta imágenes del frente y dorso del DNI
  - Usa Tesseract OCR para extracción de texto
  - Busca en zona MRZ (Machine Readable Zone)
  - Aplica filtros de imagen para mejor reconocimiento
- **Validaciones**:
  - Verifica formato de imagen (JPEG/PNG)
  - Límite de tamaño (8MB)
  - Validación MIME type
- **Algoritmo**:
  ```python
  # Busca patrones de 8 dígitos en MRZ
  digits = re.findall(r'\d{8}', mrz_text)
  # También busca formato XX.XXX.XXX
  digits += re.findall(r'\d{2}\.\d{3}\.\d{3}')
  ```

### Funciones Auxiliares Internas

#### `bytes_to_cv2(b: bytes)`
**Descripción**: Convierte bytes de imagen a formato OpenCV.
- **Uso**: Interno para procesamiento de imágenes DNI
- **Retorna**: Imagen en formato cv2
- **Error**: ValueError si no puede decodificar

#### `extract_from_mrz(img_color, size: tuple)`
**Descripción**: Extrae datos de la zona MRZ del documento.
- **Uso**: Interno para OCR de DNI
- **Funcionalidad**:
  - Redimensiona imagen
  - Aplica filtros de nitidez
  - Busca líneas con patrones MRZ ('<<')
  - Extrae secuencias numéricas

---

## 3. API de Autenticación (auth.py)

### Funciones de Login

#### `login(session: SessionDep, credentials: UserAuth)`
**Descripción**: Autentica usuarios regulares del sistema.
- **Método HTTP**: POST
- **Ruta**: `/auth/login`
- **Rate Limiting**: Máximo 10 segundos entre intentos
- **Funcionalidad**:
  - Valida credenciales (email/contraseña)
  - Genera tokens JWT (access + refresh)
  - Actualiza último login
  - Asigna scopes según rol
- **Scopes generados**:
  - `admin`: Para administradores
  - `superuser`: Para superusuarios
  - `user`: Para usuarios regulares
  - `active`: Para usuarios activos
- **Retorna**: Tokens de acceso y actualización

#### `doc_login(session: SessionDep, credentials: DoctorAuth)`
**Descripción**: Autentica médicos del sistema.
- **Método HTTP**: POST
- **Ruta**: `/auth/doc/login`
- **Rate Limiting**: Máximo 10 segundos entre intentos
- **Funcionalidad**:
  - Valida credenciales de médico
  - Genera tokens específicos para médicos
  - Incluye información de especialidad
- **Scopes**: `doc`, `active`
- **Retorna**: Token + información del médico

### Funciones de Tokens

#### `refresh(request: Request, user: User)`
**Descripción**: Renueva tokens de acceso usando refresh token.
- **Método HTTP**: GET
- **Ruta**: `/auth/refresh`
- **Autenticación**: Refresh token válido
- **Funcionalidad**:
  - Valida refresh token
  - Genera nuevos tokens
  - Mantiene scopes existentes
  - Maneja tanto usuarios como médicos

#### `get_scopes(request: Request)`
**Descripción**: Obtiene los scopes del usuario autenticado.
- **Método HTTP**: GET
- **Ruta**: `/auth/scopes`
- **Autenticación**: Requerida
- **Retorna**: Lista de permisos/scopes del usuario

#### `decode_hex(data: OauthCodeInput)`
**Descripción**: Decodifica datos hexadecimales.
- **Método HTTP**: POST
- **Ruta**: `/auth/decode/`
- **Uso**: Decodificación de códigos OAuth
- **Funcionalidad**: Convierte hex a datos legibles

### Funciones de Logout

#### `logout(request: Request, authorization: str)`
**Descripción**: Cierra sesión del usuario.
- **Método HTTP**: DELETE
- **Ruta**: `/auth/logout`
- **Autenticación**: Requerida
- **Funcionalidad**:
  - Invalida el token actual
  - Añade token a lista de tokens baneados
  - Previene reutilización del token
- **Seguridad**: Token queda permanentemente invalidado

### Funciones OAuth

#### `oauth_login(service: str)`
**Descripción**: Inicia flujo de autenticación OAuth.
- **Método HTTP**: GET
- **Ruta**: `/oauth/{service}/`
- **Servicios soportados**: Google
- **Funcionalidad**:
  - Redirige a proveedor OAuth
  - Inicia flujo de autorización
  - Maneja diferentes servicios

#### `google_callback(request: Request)`
**Descripción**: Maneja respuesta de Google OAuth.
- **Método HTTP**: GET
- **Ruta**: `/oauth/webhook/google_callback`
- **Funcionalidad**:
  - Procesa código de autorización
  - Crea/autentica usuario con datos de Google
  - Envía emails de bienvenida para nuevos usuarios
  - Envía credenciales temporales
- **Emails enviados**:
  - Email de bienvenida
  - Credenciales de cuenta Google vinculada

---

## 4. API del Área Médica (medic_area.py)

### 4.1 Departamentos (departments)

#### `get_departments(request: Request, session: SessionDep)`
**Descripción**: Obtiene lista de todos los departamentos médicos.
- **Método HTTP**: GET
- **Ruta**: `/medic/departments/`
- **Autenticación**: Requerida
- **Retorna**: Departamentos con sus especialidades
- **Datos incluidos**: ID, nombre, descripción, ubicación, especialidades

#### `get_department_by_id(request: Request, department_id: UUID, session: SessionDep)`
**Descripción**: Obtiene un departamento específico.
- **Método HTTP**: GET
- **Ruta**: `/medic/departments/{department_id}/`
- **Parámetros**: `department_id` - UUID del departamento
- **Retorna**: Departamento con especialidades detalladas

#### `add_department(request: Request, department: DepartmentCreate, session: SessionDep)`
**Descripción**: Crea un nuevo departamento.
- **Método HTTP**: POST
- **Ruta**: `/medic/departments/add/`
- **Autenticación**: Solo superusuarios
- **Validación**: Verifica permisos de superusuario
- **Campos**: nombre, descripción, location_id

#### `delete_department_by_id(request: Request, department_id: UUID, session: SessionDep)`
**Descripción**: Elimina un departamento.
- **Método HTTP**: DELETE
- **Ruta**: `/medic/departments/delete/{department_id}/`
- **Autenticación**: Solo superusuarios
- **Precaución**: Elimina en cascada especialidades relacionadas

#### `update_department(request: Request, department_id: UUID, department: DepartmentUpdate, session: SessionDep)`
**Descripción**: Actualiza información de un departamento.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/departments/update/{department_id}/`
- **Autenticación**: Solo superusuarios
- **Campos actualizables**: nombre, descripción, location_id

### 4.2 Horarios Médicos (schedules)

#### `get_medical_schedules(request: Request, session: SessionDep)`
**Descripción**: Obtiene todos los horarios médicos.
- **Método HTTP**: GET
- **Ruta**: `/medic/schedules/`
- **Retorna**: Horarios con médicos asignados
- **Datos**: día, hora inicio, hora fin, médicos

#### `get_schedule_by_id(session: SessionDep, schedule_id: UUID)`
**Descripción**: Obtiene un horario específico.
- **Método HTTP**: GET
- **Ruta**: `/medic/schedules/{schedule_id}`
- **Retorna**: Horario detallado con médicos

#### `days_by_availability(request: Request, speciality_id: UUID, session: SessionDep)`
**Descripción**: Obtiene días disponibles por especialidad.
- **Método HTTP**: GET
- **Ruta**: `/medic/schedules/available/days/{speciality_id}`
- **Funcionalidad**:
  - Busca médicos de la especialidad
  - Agrupa horarios por día
  - Calcula rangos de tiempo disponibles
  - Optimiza horarios solapados
- **Algoritmo**:
  ```python
  # Combina horarios del mismo día
  if start > schedule.start_time and end > schedule.end_time:
      dict_days[day] = (schedule.start_time, end)
  ```

#### `add_schedule(medical_schedule: MedicalScheduleCreate, session: SessionDep)`
**Descripción**: Crea un nuevo horario médico.
- **Método HTTP**: POST
- **Ruta**: `/medic/schedules/add/`
- **Campos**: día, hora_inicio, hora_fin
- **Validación**: Formato de día según enum DayOfWeek

#### `update_schedule(schedule: MedicalScheduleUpdate, session: SessionDep)`
**Descripción**: Actualiza un horario existente.
- **Método HTTP**: PUT
- **Ruta**: `/medic/schedules/update/`
- **Documentación especial**: Incluye documentación detallada sobre enum DayOfWeek
- **Validación**: Días válidos (Monday-Sunday)

#### `add_doctor_by_id(session: SessionDep, doc_id: UUID, schedule_id: UUID)`
**Descripción**: Asigna un médico a un horario.
- **Método HTTP**: PUT
- **Ruta**: `/medic/schedules/add/doctor/`
- **Parámetros Query**: doc_id, schedule_id
- **Funcionalidad**: Vincula médico con horario específico

### 4.3 Médicos (doctors)

#### `get_doctors(session: SessionDep)`
**Descripción**: Lista todos los médicos del sistema.
- **Método HTTP**: GET
- **Ruta**: `/medic/doctors/`
- **Retorna**: Información completa de médicos
- **Campos**: datos personales, especialidad, estado, horarios

#### `get_doctor_by_id(doctor_id: UUID, session: SessionDep)`
**Descripción**: Obtiene un médico específico.
- **Método HTTP**: GET
- **Ruta**: `/medic/doctors/{doctor_id}/`
- **Retorna**: Médico con horarios detallados
- **Error**: 404 si no existe

#### `me_doctor(request: Request, session: SessionDep)`
**Descripción**: Perfil del médico autenticado.
- **Método HTTP**: GET
- **Ruta**: `/medic/doctors/me`
- **Autenticación**: Solo médicos
- **Retorna**: Perfil completo con horarios

#### `get_patients_by_doctor(request: Request, doctor_id: UUID, session: SessionDep)`
**Descripción**: Lista pacientes atendidos por un médico.
- **Método HTTP**: GET
- **Ruta**: `/medic/doctors/{doctor_id}/patients`
- **Funcionalidad**: Extrae pacientes de citas médicas
- **Retorna**: Lista de usuarios/pacientes

#### `get_doctor_stats_by_id(request: Request, doctor_id: str, session: SessionDep)`
**Descripción**: Obtiene métricas estadísticas del médico.
- **Método HTTP**: GET
- **Ruta**: `/medic/doctors/{doctor_id}/stats`
- **Funcionalidad**: Usa DoctorRepository para calcular métricas
- **Retorna**: Estadísticas de desempeño

#### `add_doctor(request: Request, doctor: DoctorCreate, session: SessionDep)`
**Descripción**: Registra un nuevo médico.
- **Método HTTP**: POST
- **Ruta**: `/medic/doctors/add/`
- **Autenticación**: Admin/Superusuario
- **Funcionalidad**:
  - Crea cuenta de médico
  - Asigna especialidad
  - Hashea contraseña
- **Campos**: datos personales, especialidad, estado

#### `update_doctor(request: Request, doctor_id: UUID, session: SessionDep, doctor: DoctorUpdate)`
**Descripción**: Actualiza información del médico.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/doctors/update/{doctor_id}/`
- **Autenticación**: Médico propietario o superusuario
- **Funcionalidad especial**:
  - Maneja estados del médico (disponible/ocupado/offline)
  - Actualiza disponibilidad automáticamente
- **Estados**:
  - `available`: Médico disponible
  - `busy`: Médico ocupado
  - `offline`: Médico desconectado

#### `update_speciality(request: Request, doctor_id: UUID, session: SessionDep, doctor_form: DoctorSpecialityUpdate)`
**Descripción**: Cambia especialidad del médico.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/doctors/update/{doctor_id}/speciality`
- **Autenticación**: Médico propietario o superusuario
- **Funcionalidad**: Actualiza speciality_id

#### `update_doctor_password(request: Request, doctor_id: UUID, session: SessionDep, password: DoctorPasswordUpdate)`
**Descripción**: Cambia contraseña del médico.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/doctors/update/{doctor_id}/password`
- **Autenticación**: Médico propietario o superusuario
- **Seguridad**: Hashea nueva contraseña

#### `ban_doc(request: Request, doc_id: UUID, session: SessionDep)`
**Descripción**: Banea un médico.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/doctors/ban/{doc_id}/`
- **Autenticación**: Solo superusuarios
- **Funcionalidad**: Desactiva cuenta del médico

### 4.4 Ubicaciones (locations)

#### `get_locations(request: Request, session: SessionDep)`
**Descripción**: Lista ubicaciones básicas.
- **Método HTTP**: GET
- **Ruta**: `/medic/locations/`
- **Retorna**: ID, nombre, descripción de ubicaciones

#### `get_locations_all_data(request: Request, session: SessionDep)`
**Descripción**: Ubicaciones con datos completos jerárquicos.
- **Método HTTP**: GET
- **Ruta**: `/medic/locations/all`
- **Funcionalidad**:
  - Ubicaciones → Departamentos → Especialidades → Servicios/Médicos
  - Estructura completa anidada
- **Uso**: Para construir menús jerárquicos

#### `set_location(request: Request, session: SessionDep, location: LocationCreate)`
**Descripción**: Crea nueva ubicación.
- **Método HTTP**: POST
- **Ruta**: `/medic/locations/add/`
- **Autenticación**: Solo superusuarios

### 4.5 Servicios (services)

#### `get_services(request: Request, session: SessionDep)`
**Descripción**: Lista todos los servicios médicos.
- **Método HTTP**: GET
- **Ruta**: `/medic/services/`
- **Retorna**: Servicios con precios e iconos

#### `set_service(request: Request, session: SessionDep, service: ServiceCreate)`
**Descripción**: Crea nuevo servicio médico.
- **Método HTTP**: POST
- **Ruta**: `/medic/services/add`
- **Autenticación**: Solo superusuarios
- **Campos**: nombre, descripción, precio, especialidad, código de icono

#### `update_service(request: Request, session: SessionDep, service_id: UUID, service: ServiceUpdate)`
**Descripción**: Actualiza servicio existente.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/services/update/{service_id}/`
- **Funcionalidad**: Actualización parcial de campos
- **Método**: `exclude_unset=True` para actualizar solo campos modificados

### 4.6 Especialidades (specialities)

#### `get_specialities(request: Request, session: SessionDep)`
**Descripción**: Lista especialidades con servicios y médicos.
- **Método HTTP**: GET
- **Ruta**: `/medic/specialities/`
- **Retorna**: Especialidades con servicios asociados y médicos

#### `add_speciality(request: Request, session: SessionDep, specialty: SpecialtyCreate)`
**Descripción**: Crea nueva especialidad.
- **Método HTTP**: POST
- **Ruta**: `/medic/specialities/add/`
- **Autenticación**: Solo superusuarios

### 4.7 Chat en Tiempo Real (chat)

#### Clase `ConnectionManager`
**Descripción**: Gestiona conexiones WebSocket para chat entre médicos.
- **Funcionalidades**:
  - `connect(user_id, websocket)`: Establece conexión
  - `disconnect(user_id)`: Cierra conexión
  - `send_personal_message(message, user_id)`: Mensaje directo
  - `broadcast(message)`: Mensaje a todos
  - `is_connected(doc_id)`: Verifica conexión activa

#### `get_chats(session: SessionDep)`
**Descripción**: Lista todos los chats disponibles.
- **Método HTTP**: GET
- **Ruta**: `/medic/chat/`
- **Retorna**: Chats con información de médicos participantes

#### `create_chat(request: Request, session: SessionDep, doc_2_id)`
**Descripción**: Crea nuevo chat entre médicos.
- **Método HTTP**: POST
- **Ruta**: `/medic/chat/add`
- **Autenticación**: Solo médicos
- **Funcionalidad**: Crea sala de chat entre dos médicos

#### `websocket_chat(websocket: WebSocket, session: SessionDep, chat_id, data)`
**Descripción**: Endpoint WebSocket para chat en tiempo real.
- **Protocolo**: WebSocket
- **Ruta**: `/medic/ws/chat/{chat_id}`
- **Autenticación**: JWT via WebSocket
- **Funcionalidad**:
  - Valida permisos de médico en chat
  - Recibe y almacena mensajes
  - Envía mensajes en tiempo real
  - Maneja desconexiones

### 4.8 Turnos (turns)

#### `get_turns(request: Request, session: SessionDep)`
**Descripción**: Lista todos los turnos (solo superusuarios).
- **Método HTTP**: GET
- **Ruta**: `/medic/turns/`
- **Autenticación**: Solo superusuarios
- **Retorna**: Turnos con servicios y citas asociadas

#### `get_turns_by_user_id(request: Request, session: SessionDep, user_id: UUID)`
**Descripción**: Obtiene turnos de un usuario específico.
- **Método HTTP**: GET
- **Ruta**: `/medic/turns/{user_id}`
- **Funcionalidad**:
  - Lista turnos del usuario
  - Incluye información del médico
  - Incluye servicios solicitados
- **Serialización**: Funciones helper para departamentos y especialidades

#### `create_turn(request: Request, session: SessionDep, turn: TurnsCreate)`
**Descripción**: Crea nuevo turno médico con procesamiento de pago.
- **Método HTTP**: POST
- **Ruta**: `/medic/turns/add`
- **Funcionalidad compleja**:
  - Valida disponibilidad de médico
  - Crea turno y cita asociada
  - Calcula precio total con descuentos
  - Integra con Stripe para pagos
  - Maneja seguros médicos
- **Retorna**: Turno creado + URL de pago

#### `update_state(request: Request, turn_id: UUID, new_state: str, session: SessionDep)`
**Descripción**: Actualiza estado de un turno.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/turns/update/state`
- **Estados válidos**:
  - `waiting`: En espera
  - `accepted`: Aceptado
  - `finished`: Finalizado
  - `cancelled`: Cancelado
  - `rejected`: Rechazado
- **Validación**: Estados finales no modificables (excepto superusuarios)

### 4.9 Citas (appointments)

#### `get_appointments(request: Request, session: SessionDep)`
**Descripción**: Lista todas las citas médicas.
- **Método HTTP**: GET
- **Ruta**: `/medic/appointments/`
- **Autenticación**: Superusuarios o médicos
- **Retorna**: Citas con información de turnos asociados

### 4.10 Seguros Médicos (health_insurance)

#### `get_health_insurance(request: Request, session: SessionDep)`
**Descripción**: Lista todos los seguros médicos disponibles.
- **Método HTTP**: GET
- **Ruta**: `/medic/health_insurance/`
- **Retorna**: Seguros con descuentos aplicables

#### `create_health_insurance(request: Request, session: SessionDep, payload: HealthInsuranceCreate)`
**Descripción**: Crea nuevo seguro médico.
- **Método HTTP**: POST
- **Ruta**: `/medic/health_insurance/create`
- **Campos**: nombre, descripción, porcentaje de descuento

#### `update_health_insurance(request: Request, session: SessionDep, hi_id: UUID, payload: HealthInsuranceUpdate)`
**Descripción**: Actualiza seguro médico existente.
- **Método HTTP**: PATCH
- **Ruta**: `/medic/health_insurance/update/{hi_id}`
- **Funcionalidad**: Actualización parcial con `exclude_unset=True`

---

## 5. API de Cajas (cashes.py)

### Funciones de Pagos

#### `pay_success(session: SessionDep, a: str)`
**Descripción**: Maneja confirmación de pago exitoso desde Stripe.
- **Método HTTP**: GET
- **Ruta**: `/cashes/pay/success`
- **Funcionalidad**:
  - Decodifica datos de pago hexadecimales
  - Crea registro de transacción
  - Redirige a panel de usuario
- **Parámetros**: `a` - datos de pago codificados en hex
- **Redirección**: 
  - Éxito: `/user_panel/appointments?success=true`
  - Error: `/user_panel/appointments?success=false&services=...`

#### `pay_cansel(b: str)`
**Descripción**: Maneja cancelación de pago.
- **Método HTTP**: GET
- **Ruta**: `/cashes/pay/cancel`
- **Funcionalidad**: Decodifica datos y redirige
- **Redirección**: Vuelta al panel de citas

### Funciones de Consulta

#### `get_cashes(request: Request, session: SessionDep)`
**Descripción**: Obtiene registros de transacciones.
- **Método HTTP**: GET
- **Ruta**: `/cashes/`
- **Autenticación**: Solo administradores
- **Retorna**: Lista de transacciones con:
  - Ingresos
  - Gastos
  - Fecha y hora
  - Balance

---

## 6. API del Asistente IA (ai_assistant.py)

### `get_ai_service()`
**Descripción**: Función de dependencia para obtener servicio de IA.
- **Tipo**: Dependency
- **Retorna**: Instancia de AIAssistantService
- **Uso**: Inyección de dependencias en endpoints

### Funciones de Chat

#### `chat_with_assistant(request: AIAssistantRequest, ai_service: AIAssistantService)`
**Descripción**: Chat principal con el asistente de IA.
- **Método HTTP**: POST
- **Ruta**: `/ai-assistant/chat`
- **Funcionalidades del IA**:
  - Gestión de citas médicas
  - Información de médicos
  - Gestión de horarios
  - Generación de reportes
  - Notificaciones y emails
- **Procesamiento**: Natural Language Processing

#### `simple_chat(message: str, user_context: Dict, ai_service: AIAssistantService)`
**Descripción**: Endpoint simplificado de chat.
- **Método HTTP**: POST
- **Ruta**: `/ai-assistant/simple-chat`
- **Uso**: Integración simple con texto plano
- **Parámetros**: 
  - `message`: Mensaje del usuario
  - `user_context`: Contexto opcional

### Funciones de Workflows

#### `execute_ai_workflow(request: AIWorkflowRequest, ai_service: AIAssistantService)`
**Descripción**: Ejecuta workflows predefinidos de IA.
- **Método HTTP**: POST
- **Ruta**: `/ai-assistant/workflow`
- **Workflows disponibles**:
  - `smart_appointment_booking`: Reserva inteligente de citas
  - `doctor_recommendation`: Recomendación de médicos con IA
  - `schedule_optimization`: Optimización de horarios

### Funciones de Información

#### `get_ai_capabilities(ai_service: AIAssistantService)`
**Descripción**: Obtiene capacidades del asistente IA.
- **Método HTTP**: GET
- **Ruta**: `/ai-assistant/capabilities`
- **Retorna**: Información sobre:
  - Modelo de IA utilizado
  - Interfaces disponibles
  - Características soportadas

#### `get_smart_suggestions(request: AISuggestionRequest, ai_service: AIAssistantService)`
**Descripción**: Genera sugerencias inteligentes contextuales.
- **Método HTTP**: POST
- **Ruta**: `/ai-assistant/suggestions`
- **Contexto considerado**:
  - Horario actual y horarios de trabajo
  - Rol y permisos del usuario
  - Página o flujo de trabajo actual
  - Estado del sistema y acciones disponibles

### Funciones de Monitoreo

#### `ai_health_check()`
**Descripción**: Verificación de salud del servicio de IA.
- **Método HTTP**: GET
- **Ruta**: `/ai-assistant/health`
- **Retorna**: Estado del servicio
- **Información incluida**:
  - Estado de salud
  - Modelo de IA en uso
  - Versión del modelo
  - Cantidad de interfaces
  - Cantidad de características

---

## 7. Core - Autenticación (core/auth.py)

### Funciones de Codificación/Decodificación

#### `encode(data: object) → bytes`
**Descripción**: Función polimórfica para codificar diferentes tipos de datos.
- **Tipos soportados**: 
  - `str`: Texto plano
  - `UUID`: Identificadores únicos
  - `BaseModel`: Modelos Pydantic
  - `dict`, `list`, `tuple`: Estructuras JSON
  - `int`, `float`, `bool`: Tipos primitivos
  - `None`: Valor nulo
- **Algoritmo**: Usa Fernet para encriptación simétrica
- **Serialización**: JSON con `dumps()` para objetos complejos

#### `decode(data: bytes, dtype: Type[T]) → T | Any`
**Descripción**: Decodifica datos encriptados con tipo específico.
- **Parámetros**:
  - `data`: Datos encriptados en bytes
  - `dtype`: Tipo esperado del resultado
- **Funcionalidad**:
  - Desencripta usando Fernet
  - Deserializa JSON cuando aplicable
  - Valida con Pydantic si es BaseModel
- **Manejo de errores**: ValueError para tokens inválidos

### Funciones de JWT

#### `gen_token(payload: dict, refresh: bool = False) → str`
**Descripción**: Genera tokens JWT para autenticación.
- **Parámetros**:
  - `payload`: Datos del usuario y scopes
  - `refresh`: Si es token de renovación
- **Configuración automática**:
  - `iat`: Timestamp de emisión
  - `iss`: Emisor (nombre de API + versión)
  - `exp`: Expiración (15 min normal, 1 día refresh)
- **Algoritmo**: HS256 con clave secreta

#### `decode_token(token: str) → dict`
**Descripción**: Decodifica y valida tokens JWT.
- **Validaciones**:
  - Firma del token
  - Fecha de expiración
  - Formato válido
- **Leeway**: 20 segundos de tolerancia
- **Error**: ValueError para tokens inválidos

### Funciones de Rate Limiting

#### `time_out(seconds: float = 1.0, max_trys: int = 5)`
**Descripción**: Decorador para limitar velocidad de requests.
- **Funcionalidad**:
  - Rastrea último acceso por IP
  - Limita tiempo entre requests
  - Cuenta intentos fallidos
  - Almacena estado en storage temporal
- **Parámetros**:
  - `seconds`: Tiempo mínimo entre requests
  - `max_trys`: Máximo intentos permitidos
- **Errores**: HTTP 429 Too Many Requests

### Clases de Autenticación

#### `JWTBearer`
**Descripción**: Clase para autenticación JWT en HTTP requests.
- **Método principal**: `__call__(request: Request, authorization: str)`
- **Funcionalidad**:
  - Extrae token del header Authorization
  - Valida formato "Bearer {token}"
  - Decodifica y valida token
  - Verifica tokens baneados
  - Carga usuario de base de datos
  - Establece scopes en request.state
- **Validaciones especiales**:
  - Previene uso de refresh tokens en endpoints normales
  - Maneja tanto usuarios como médicos
  - Envía emails de warning para cuentas Google

#### `JWTWebSocket`
**Descripción**: Autenticación JWT para conexiones WebSocket.
- **Método principal**: `__call__(websocket: WebSocket)`
- **Diferencias con JWTBearer**:
  - Token viene en query parameters
  - Formato: `?token=Bearer_{token}`
  - Cierra conexión WebSocket en caso de error
  - Retorna tupla (usuario, scopes)
- **Manejo de errores**: Códigos de cierre WebSocket específicos

---

## 8. Core - Base de Datos (db/main.py)

### Configuración de Base de Datos

#### `engine`
**Descripción**: Motor SQLAlchemy para conexión a base de datos.
- **Configuración**:
  - URL desde variable de entorno
  - `echo=False`: Sin logs SQL en producción
  - `future=True`: Usa SQLAlchemy 2.0 style
  - `pool_pre_ping=True`: Verifica conexiones

### Funciones de Inicialización

#### `init_db()`
**Descripción**: Inicializa esquema de base de datos.
- **Funcionalidad**:
  - Crea todas las tablas definidas en modelos
  - Usa SQLModel.metadata.create_all()
  - Operación idempotente (no duplica tablas)

#### `migrate()`
**Descripción**: Ejecuta migraciones de Alembic.
- **Comando**: `alembic upgrade head`
- **Funcionalidad**:
  - Aplica migraciones pendientes
  - Captura output para debugging
  - Maneja stdout y stderr
- **Modo debug**: Muestra logs detallados

#### `set_admin()`
**Descripción**: Crea usuario administrador inicial.
- **Funcionalidad**:
  - Verifica si admin ya existe
  - Crea admin_user desde configuración
  - Maneja IntegrityError (admin existente)
  - Commit automático de la transacción
- **Seguridad**: Solo crea si no existe

### Funciones de Diagnóstico

#### `test_db() → Tuple[float, bool]`
**Descripción**: Prueba conectividad y rendimiento de BD.
- **Funcionalidad**:
  - Mide tiempo de respuesta
  - Ejecuta query simple (SELECT User)
  - Valida que retorne datos
- **Retorna**: 
  - `float`: Tiempo en segundos
  - `bool`: Éxito de la operación
- **Uso**: Health checks y monitoreo

### Gestión de Sesiones

#### `get_session()`
**Descripción**: Generador de sesiones de base de datos.
- **Patrón**: Context manager con yield
- **Funcionalidad**:
  - Crea sesión nueva por request
  - Garantiza cierre automático
  - Manejo de transacciones
- **Uso**: Dependency injection

#### `SessionDep`
**Descripción**: Tipo anotado para inyección de dependencias.
- **Definición**: `Annotated[Session, Depends(get_session)]`
- **Uso**: Parameter type hint en funciones de API
- **Beneficio**: Type safety + dependency injection

### Metadatos

#### `metadata`
**Descripción**: Metadatos de SQLModel para migraciones.
- **Uso**: Alembic y herramientas de migración
- **Contenido**: Definiciones de tablas y relaciones

---

## 9. Modelos de Datos (models.py)

### Clases Base y Mixins

#### `BaseUser`
**Descripción**: Modelo base para usuarios del sistema.
- **Hereda de**: SQLModel
- **Campos principales**:
  - `name`: Nombre de usuario (VARCHAR 32)
  - `email`: Email único con índice
  - `password`: Contraseña hasheada
  - `first_name`, `last_name`: Nombres
  - `dni`: Documento de identidad (8 caracteres)
  - `telephone`: Teléfono opcional
  - `address`: Dirección
  - `blood_type`: Tipo de sangre
  - `url_image_profile`: URL de imagen de perfil
- **Campos de estado**:
  - `is_active`: Usuario activo
  - `is_admin`: Es administrador
  - `is_superuser`: Es superusuario
- **Campos de auditoría**:
  - `last_login`: Último acceso
  - `date_joined`: Fecha de registro
  - `updated_at`: Última actualización

#### Métodos de BaseUser

##### `set_url_image_profile(file_name: str)`
**Descripción**: Establece URL de imagen de perfil.
- **Funcionalidad**: Construye URL completa con dominio
- **Formato**: `{DOMINIO}/media/{modelo}/{archivo}`

##### `save_profile_image(file: UploadFile, media_root: str = "media")`
**Descripción**: Guarda imagen de perfil en sistema de archivos.
- **Funcionalidad**:
  - Valida tipo de archivo (imagen)
  - Genera nombre único
  - Crea directorio si no existe
  - Guarda archivo físicamente
  - Actualiza URL en modelo
- **Validaciones**: Solo acepta imágenes

### Enums del Sistema

#### `DoctorStates`
**Descripción**: Estados de disponibilidad de médicos.
- **Valores**:
  - `available`: Médico disponible
  - `busy`: Médico ocupado
  - `offline`: Médico fuera de línea

#### `DayOfWeek`
**Descripción**: Días de la semana para horarios.
- **Valores**: monday, tuesday, wednesday, thursday, friday, saturday, sunday

#### `TurnsState`
**Descripción**: Estados de turnos médicos.
- **Valores**:
  - `waiting`: En espera de confirmación
  - `accepted`: Turno aceptado
  - `finished`: Turno completado
  - `cancelled`: Turno cancelado
  - `rejected`: Turno rechazado

### Funciones de Validación

#### `PasswordError`
**Descripción**: Excepción personalizada para errores de contraseña.
- **Hereda de**: Exception
- **Uso**: Validación de contraseñas complejas

### Funciones de Seguridad

#### `pwd_context`
**Descripción**: Contexto de Passlib para manejo de contraseñas.
- **Algoritmo**: bcrypt
- **Configuración**: Esquemas deprecados automáticamente

Las funciones de los modelos incluyen métodos para:
- Hasheo seguro de contraseñas
- Validación de campos
- Manejo de archivos multimedia
- Relaciones entre entidades
- Auditoría automática de cambios

---

## Consideraciones Generales

### Seguridad Implementada
- **Autenticación JWT** con tokens de acceso y renovación
- **Rate limiting** para prevenir ataques de fuerza bruta
- **Hasheo de contraseñas** con bcrypt
- **Validación de permisos** por roles y scopes
- **Encriptación de datos** sensibles con Fernet
- **Invalidación de tokens** en logout

### Patrones de Diseño Utilizados
- **Repository Pattern** para acceso a datos
- **Dependency Injection** con FastAPI
- **Service Layer** para lógica de negocio
- **DTO Pattern** con Pydantic schemas
- **Observer Pattern** para eventos de modelos

### Características Técnicas
- **Base de datos**: SQLModel + SQLAlchemy 2.0
- **Migraciones**: Alembic
- **Documentación**: OpenAPI + Scalar
- **WebSockets**: Para chat en tiempo real
- **OCR**: Tesseract para procesamiento de documentos
- **Pagos**: Integración con Stripe
- **Emails**: Sistema de notificaciones
- **IA**: Asistente con NLP

### Escalabilidad
- **Arquitectura modular** por dominios
- **Separación de responsabilidades**
- **Configuración basada en environment**
- **Logging estructurado** con Rich
- **Health checks** integrados
- **Caching** con almacenamiento temporal

Esta documentación cubre todas las funciones principales del sistema hospitalario, proporcionando una referencia completa para desarrolladores y administradores del sistema.