from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.core.services.ai_assistant_service import AIAssistantService
from app.schemas.ai_assistant import (
    AIAssistantRequest,
    AIAssistantResponse,
    AIWorkflowRequest,
    AIWorkflowResponse,
    AICapabilitiesResponse,
    AISuggestionRequest,
    AISuggestionResponse
)

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

# Dependency to get AI service
def get_ai_service() -> AIAssistantService:
    """
    Función de dependencia para obtener instancia del servicio de IA.
    
    Crea y retorna una nueva instancia del servicio de asistente de IA
    para ser inyectada en los endpoints como dependencia.
    
    Returns:
        AIAssistantService: Instancia del servicio de IA configurada
        
    Note:
        - Usado como FastAPI Dependency
        - Crea nueva instancia por request
        - Maneja configuración automática del servicio
    """
    return AIAssistantService()


@router.post("/chat", response_model=AIAssistantResponse)
async def chat_with_assistant(
    request: AIAssistantRequest,
    ai_service: AIAssistantService = Depends(get_ai_service)
):
    """
    Chat with the AI assistant using natural language.
    
    The AI assistant can help with:
    - Appointment management
    - Doctor information
    - Schedule management
    - Report generation
    - Notifications and emails
    """
    try:
        response = await ai_service.process_user_request(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@router.post("/workflow", response_model=AIWorkflowResponse)
async def execute_ai_workflow(
    request: AIWorkflowRequest,
    ai_service: AIAssistantService = Depends(get_ai_service)
):
    """
    Execute predefined AI workflows.
    
    Available workflows:
    - smart_appointment_booking: Intelligent appointment scheduling
    - doctor_recommendation: AI-powered doctor matching
    - schedule_optimization: Optimize schedules using AI
    """
    try:
        response = await ai_service.execute_workflow(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing workflow: {str(e)}")


@router.get("/capabilities", response_model=AICapabilitiesResponse)
async def get_ai_capabilities(
    ai_service: AIAssistantService = Depends(get_ai_service)
):
    """
    Get information about AI assistant capabilities and features.
    """
    try:
        capabilities = ai_service.get_capabilities()
        return capabilities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting capabilities: {str(e)}")


@router.post("/suggestions", response_model=AISuggestionResponse)
async def get_smart_suggestions(
    request: AISuggestionRequest,
    ai_service: AIAssistantService = Depends(get_ai_service)
):
    """
    Get AI-powered smart suggestions based on current context.
    
    Provides intelligent suggestions based on:
    - Current time and business hours
    - User role and permissions
    - Current page or workflow context
    - System state and available actions
    """
    try:
        suggestions = await ai_service.get_smart_suggestions(request)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


@router.post("/simple-chat")
async def simple_chat(
    message: str,
    user_context: Dict[str, Any] = None,
    ai_service: AIAssistantService = Depends(get_ai_service)
):
    """
    Simple chat endpoint that accepts a plain text message and returns a response.
    
    This is a simplified version of the main chat endpoint for easier integration.
    """
    try:
        response = await ai_service.chat_with_assistant(message, user_context)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in simple chat: {str(e)}")


@router.get("/health")
async def ai_health_check():
    """
    Endpoint de verificación de salud del servicio de IA.
    
    Proporciona información sobre el estado y configuración del asistente
    de IA, incluyendo modelo utilizado y capacidades disponibles.
    
    Returns:
        dict: Estado de salud del servicio con información detallada:
            - status (str): 'healthy' o 'unhealthy'  
            - ai_model (str): Nombre del modelo de IA en uso
            - version (str): Versión del modelo
            - interfaces_count (int): Número de interfaces disponibles
            - features_count (int): Número de características soportadas
            - error (str): Mensaje de error si status es 'unhealthy'
            
    Note:
        - No requiere autenticación
        - Útil para monitoreo y diagnóstico
        - Maneja errores graciosamente retornando estado 'unhealthy'
    """
    try:
        ai_service = AIAssistantService()
        capabilities = ai_service.get_capabilities()
        
        return {
            "status": "healthy",
            "ai_model": capabilities.model.get("name", "unknown"),
            "version": capabilities.model.get("version", "unknown"),
            "interfaces_count": len(capabilities.interfaces_available),
            "features_count": len(capabilities.features)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }