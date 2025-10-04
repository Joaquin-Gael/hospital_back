from typing import Dict, Any, List
from app.core.interfaces.ai_assistant import AIAssistantInterface
from app.schemas.ai_assistant import (
    AIAssistantRequest, 
    AIAssistantResponse,
    AIWorkflowRequest,
    AIWorkflowResponse,
    AICapabilitiesResponse,
    AISuggestionRequest,
    AISuggestionResponse
)
from app.storage.command.main import console


class AIAssistantService:
    """
    Service layer for AI Assistant operations.
    Handles business logic and coordinates between API and AI interface.
    """
    
    def __init__(self):
        self.ai_interface = AIAssistantInterface()
    
    async def process_user_request(self, request: AIAssistantRequest) -> AIAssistantResponse:
        """
        Process a user request through the AI assistant.
        
        Args:
            request: AIAssistantRequest containing the user's natural language request
            
        Returns:
            AIAssistantResponse with the AI's response and any relevant data
        """
        try:
            # Process the request through the AI interface
            result = await self.ai_interface.process_natural_language_request(
                request.request, 
                request.user_context
            )
            
            # Convert to response schema
            return AIAssistantResponse(
                success=result.get("success", True),
                message=result.get("message", ""),
                type=result.get("type", "general"),
                data=result.get("data"),
                suggestions=result.get("suggestions")
            )
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return AIAssistantResponse(
                success=False,
                message=f"Error processing request: {str(e)}",
                type="error"
            )
    
    async def execute_workflow(self, request: AIWorkflowRequest) -> AIWorkflowResponse:
        """
        Execute an AI workflow.
        
        Args:
            request: AIWorkflowRequest with workflow name and parameters
            
        Returns:
            AIWorkflowResponse with the execution result
        """
        try:
            result = await self.ai_interface.execute_ai_workflow(
                request.workflow_name,
                request.parameters
            )
            
            return AIWorkflowResponse(
                success=result.get("success", True),
                message=result.get("message", ""),
                workflow=request.workflow_name,
                result=result
            )
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return AIWorkflowResponse(
                success=False,
                message=f"Error executing workflow: {str(e)}",
                workflow=request.workflow_name
            )
    
    def get_capabilities(self) -> AICapabilitiesResponse:
        """
        Get AI assistant capabilities.
        
        Returns:
            AICapabilitiesResponse with current capabilities
        """
        try:
            capabilities = self.ai_interface.get_ai_capabilities()
            
            return AICapabilitiesResponse(
                model=capabilities["model"],
                interfaces_available=capabilities["interfaces_available"],
                features=capabilities["features"],
                workflows=[
                    "smart_appointment_booking",
                    "doctor_recommendation", 
                    "schedule_optimization"
                ]
            )
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return AICapabilitiesResponse(
                model={"error": "Could not load model info"},
                interfaces_available=[],
                features=[],
                workflows=[]
            )
    
    async def get_smart_suggestions(self, request: AISuggestionRequest) -> AISuggestionResponse:
        """
        Get AI-powered smart suggestions.
        
        Args:
            request: AISuggestionRequest with context information
            
        Returns:
            AISuggestionResponse with relevant suggestions
        """
        try:
            # Add user role to context if provided
            context = request.context.copy()
            if request.user_role:
                context["user_role"] = request.user_role
            if request.current_page:
                context["current_page"] = request.current_page
            
            suggestions = await self.ai_interface.generate_smart_suggestions(context)
            
            return AISuggestionResponse(
                suggestions=suggestions,
                context_analyzed=context
            )
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return AISuggestionResponse(
                suggestions=[],
                context_analyzed=request.context
            )
    
    async def chat_with_assistant(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simple chat interface with the AI assistant.
        
        Args:
            message: User's message
            user_context: Optional user context
            
        Returns:
            Dict with the assistant's response
        """
        try:
            request = AIAssistantRequest(
                request=message,
                user_context=user_context
            )
            
            response = await self.process_user_request(request)
            
            return {
                "response": response.message,
                "type": response.type,
                "data": response.data,
                "suggestions": response.suggestions,
                "success": response.success
            }
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return {
                "response": f"Lo siento, ocurrió un error: {str(e)}",
                "type": "error",
                "success": False
            }