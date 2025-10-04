# AI Assistant Module Documentation

## Descripción

El módulo AI Assistant proporciona capacidades de inteligencia artificial para asistir en todas las operaciones del sistema hospitalario. Actúa como un hub central que puede acceder a todas las interfaces del sistema y proporcionar respuestas inteligentes a consultas en lenguaje natural.

## Arquitectura

```
app/
├── core/
│   ├── interfaces/
│   │   ├── ai_assistant.py          # Interfaz principal de IA
│   │   ├── users.py                 # Interfaz de usuarios
│   │   ├── medic_area.py           # Interfaz de área médica
│   │   └── emails.py               # Interfaz de emails
│   └── services/
│       └── ai_assistant_service.py  # Servicio de lógica de negocio
├── api/
│   └── ai_assistant.py             # Endpoints de API
└── schemas/
    └── ai_assistant.py             # Esquemas de datos
```

## Características Principales

### 1. Procesamiento de Lenguaje Natural
- Interpreta consultas en lenguaje natural
- Enruta automáticamente a las funciones apropiadas
- Proporciona respuestas contextuales

### 2. Acceso a Todas las Interfaces
- `UserRepository`: Gestión de usuarios
- `DoctorRepository`: Información de doctores
- `TurnAndAppointmentRepository`: Citas y turnos
- `EmailService`: Servicios de email

### 3. Workflows Inteligentes
- `smart_appointment_booking`: Reserva inteligente de citas
- `doctor_recommendation`: Recomendación de doctores
- `schedule_optimization`: Optimización de horarios

### 4. Sugerencias Inteligentes
- Basadas en el contexto del usuario
- Consideran el tiempo y horarios de negocio
- Adaptadas al rol del usuario

## Uso de la API

### Endpoints Disponibles

#### 1. Chat con el Asistente
```http
POST /ai-assistant/chat
Content-Type: application/json

{
  "request": "Quiero agendar una cita con un cardiólogo",
  "user_context": {
    "user_id": "123",
    "user_role": "patient"
  }
}
```

#### 2. Ejecutar Workflow
```http
POST /ai-assistant/workflow
Content-Type: application/json

{
  "workflow_name": "smart_appointment_booking",
  "parameters": {
    "specialty": "cardiology",
    "preferred_date": "2024-01-15"
  }
}
```

#### 3. Obtener Capacidades
```http
GET /ai-assistant/capabilities
```

#### 4. Obtener Sugerencias
```http
POST /ai-assistant/suggestions
Content-Type: application/json

{
  "context": {
    "current_page": "dashboard",
    "time_of_day": "morning"
  },
  "user_role": "doctor"
}
```

#### 5. Chat Simplificado
```http
POST /ai-assistant/simple-chat?message=Mostrar mis citas de hoy
```

## Ejemplos de Uso

### Ejemplo 1: Consulta de Citas
```python
from app.core.services.ai_assistant_service import AIAssistantService
from app.schemas.ai_assistant import AIAssistantRequest

ai_service = AIAssistantService()

request = AIAssistantRequest(
    request="Mostrar mis citas de la próxima semana",
    user_context={"user_id": "patient_123"}
)

response = await ai_service.process_user_request(request)
print(response.message)
```

### Ejemplo 2: Recomendación de Doctor
```python
workflow_request = AIWorkflowRequest(
    workflow_name="doctor_recommendation",
    parameters={
        "symptoms": ["dolor de pecho", "fatiga"],
        "age": 45,
        "insurance": "premium"
    }
)

result = await ai_service.execute_workflow(workflow_request)
```

### Ejemplo 3: Sugerencias Contextuales
```python
suggestion_request = AISuggestionRequest(
    context={"current_hour": 14, "appointments_today": 3},
    user_role="doctor",
    current_page="schedule"
)

suggestions = await ai_service.get_smart_suggestions(suggestion_request)
```

## Tipos de Consultas Soportadas

### Citas y Reservas
- "Quiero agendar una cita"
- "Mostrar mis próximas citas" 
- "Cancelar mi cita del viernes"
- "¿Hay disponibilidad con el Dr. García?"

### Información de Doctores
- "Mostrar todos los cardiologos"
- "¿Qué doctores están disponibles hoy?"
- "Información del Dr. López"

### Horarios
- "¿Cuál es mi horario de mañana?"
- "Crear un nuevo turno"
- "Optimizar mi calendario"

### Reportes
- "Generar reporte de citas del mes"
- "Estadísticas de pacientes"
- "Métricas de doctores"

### Notificaciones
- "Enviar recordatorio de cita"
- "Notificar cambio de horario"

## Configuración y Personalización

### Agregar Nuevas Capacidades

Para agregar nuevas capacidades al asistente:

1. **Actualizar `model_config`** en `AIAssistantInterface.__init__()`:
```python
self.model_config = {
    "capabilities": [
        "existing_capability",
        "new_capability"  # Agregar aquí
    ]
}
```

2. **Agregar handler** en `process_natural_language_request()`:
```python
elif any(keyword in request_lower for keyword in ["new_keyword"]):
    return await self._handle_new_capability(request, user_context)
```

3. **Implementar método handler**:
```python
async def _handle_new_capability(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Implementar lógica
    pass
```

### Agregar Nuevos Workflows

```python
async def execute_ai_workflow(self, workflow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if workflow_name == "new_workflow":
        return await self._workflow_new_feature(parameters)
    # ... resto del código
```

## Estado de Desarrollo

### ✅ Implementado
- Interfaz base del AI Assistant
- Procesamiento de lenguaje natural básico
- Acceso a todas las interfaces del sistema
- Endpoints de API completos
- Schemas de datos
- Servicio de lógica de negocio
- Documentación

### 🔄 En Desarrollo
- Workflows específicos de dominio
- Integración con modelos de IA externos
- Métricas y analytics
- Cache de respuestas

### 🚀 Futuras Mejoras
- Integración con Hugging Face
- Aprendizaje automático personalizado
- Análisis de sentimientos
- Respuestas multimodales (texto, imágenes)
- Integración con FastMCP

## Testing

### Probar el Sistema

```bash
# Verificar health check
curl http://localhost:8000/api-prefix/ai-assistant/health

# Probar chat simple
curl -X POST "http://localhost:8000/api-prefix/ai-assistant/simple-chat?message=Hola"

# Obtener capacidades
curl http://localhost:8000/api-prefix/ai-assistant/capabilities
```

## Consideraciones de Seguridad

- Las consultas incluyen validación de contexto de usuario
- Acceso controlado basado en roles
- Logging completo de interacciones
- Manejo seguro de errores sin exposición de datos internos

## Escalabilidad

El módulo está diseñado para:
- Manejar múltiples sesiones concurrentes
- Escalar horizontalmente con múltiples instancias
- Integrar con sistemas de cache (Redis)
- Soportar balanceadores de carga