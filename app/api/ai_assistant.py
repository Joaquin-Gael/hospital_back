from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any

from app.core.auth import JWTBearer, time_out
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

auth = JWTBearer()

router = APIRouter(
    prefix="/ai-assistant", 
    tags=["AI-assistant"],
    dependencies=[Depends(auth)],
    responses={404: {"description": "Not found"}}
)

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
@time_out(60, 10)
async def chat_with_assistant(
    request: Request,
    user_request: AIAssistantRequest,
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
        response = await ai_service.process_user_request(user_request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")
