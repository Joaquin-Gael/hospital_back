from typing import Optional, Dict, Any, List
from sqlmodel import Session
from datetime import datetime
import os
import json
import asyncio

from transformers import AutoTokenizer, AutoModelForCausalLM

from rich.console import Console

from app.core.utils import BaseInterface
from app.core.interfaces.users import UserRepository
from app.core.interfaces.medic_area import DoctorRepository, TurnAndAppointmentRepository
from app.core.interfaces.emails import EmailService
from app.config import llm_model_name
from app.db.main import engine
from app.models import User, Doctors, Appointments, Turns

console = Console()

_model = None
_tokenizer = None

def init_model_torch_class():
    global _model
    global _tokenizer
    try:
        tokenizer = AutoTokenizer.from_pretrained(llm_model_name)
        model = AutoModelForCausalLM.from_pretrained(llm_model_name, torch_dtype="auto", device_map="auto")    
        
        _model = model
        _tokenizer = tokenizer
        
        console.print(f"AI model loaded successfully\n\nmodel name [blue]{llm_model_name}[/]", style="green")
        
    except Exception as e:
        console.print_exception(show_locals=False)
        console.print("AI model unavailable — continuing without AI features.", style="red")

class AIAssistantCapabilityError(Exception):
    """Exception raised when AI assistant lacks capability for requested operation."""
    def __init__(self, message: str = "AI Assistant cannot perform this operation."):
        self.message = message
        super().__init__(self.message)


class AIAssistantInterface(BaseInterface):
    """
    AI Assistant interface that provides intelligent capabilities across the hospital system.
    This class serves as a central hub for AI-powered operations and can access all system interfaces.
    """
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.doctor_repo = DoctorRepository()
        self.turn_appointment_repo = TurnAndAppointmentRepository()
        self.email_service = EmailService()
        
        self.model_messages = []
        self.max_history = 10
        
        # AI model configuration
        self.model_config = {
            "name": "hospital_assistant",
            "version": "1.0.0",
            "capabilities": [
                "user_assistance",
                "appointment_management", 
                "medical_scheduling",
                "doctor_consultation",
                "report_generation",
                "notification_management"
            ]
        }
        
        self.tools_promt = f"Eres un assitente de hospital llamado {self.model_config['name']}, version {self.model_config['version']}. Tienes acceso a las siguientes interfaces del sistema:\n" + \
            "- UserRepository: Gestión de usuarios (crear, actualizar, eliminar, autenticar)\n" + \
            "- DoctorRepository: Gestión de doctores (listar, buscar, disponibilidad)\n" + \
            "- TurnAndAppointmentRepository: Gestión de turnos y citas (crear, listar, modificar)\n" + \
            "- EmailService: Envío de correos electrónicos (notificaciones, recordatorios)\n" + \
            "Utiliza estas interfaces para ayudar a los usuarios con sus solicitudes de manera inteligente y eficiente.\n" + \
            "Responde en el mismo idioma en que se te pregunte, ya sea español o inglés.\n" + \
            "Si no sabes la respuesta, di que no lo sabes. No intentes inventar respuestas.\n" + \
            f"Si tienes la nesesidad de emplementar alguna de las funcionalidades del sistema, aclara en tu respuesta un sector separado de la respuesta del usuario con el titulo '### IMPLEMENTACION NECESARIA ###' y detalla  el nombre de alguna de las siguientes herramientas: [{"".join(self.model_config["capabilities"])}] \n"
            
    async def _regiter_messages(self, role: str, content: str):
        """Register a message in the conversation history."""
        self.model_messages.append({"role": role, "content": content})
        if len(self.model_messages) > self.max_history:
            self.model_messages.pop(0)
            
    async def _generate_response(self, request: str, user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate a response from the AI model based on the request and user context.
        
        Args:
            request: Natural language request from user
            user_context: Optional context about the requesting user
        Returns:
            Generated response string
        """
        
        global _tokenizer
        global _model
        
        try:
            if _model is None or _tokenizer is None:
                raise AIAssistantCapabilityError("AI model is not available")
            
            input_text = request
            if user_context:
                context_str = json.dumps(user_context)
                input_text += f"\n\n##User Context: {context_str}"
            
            input_text += f"\n\n##Tools Context: {self.tools_promt}"
            
            await self._regiter_messages("user", input_text)
            
            inputs = _tokenizer.apply_chat_template(self.model_messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to(_model.device)
            outputs = _model.generate(**inputs, max_new_tokens=150)
            response = _tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            await self._regiter_messages("assistant", response[0]["generated_text"][-1]["content"])
            
            return response[0]["generated_text"]

        except Exception as e:
            console.print_exception(show_locals=True)
            raise AIAssistantCapabilityError(f"Error generating AI response: {str(e)}")
        
    async def process_natural_language_request(self, request: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process natural language requests and route them to appropriate system functions.
        
        Args:
            request: Natural language request from user
            user_context: Optional context about the requesting user
            
        Returns:
            Dict containing response and any relevant data
        """
        try:
            # Normalize and analyze the request
            request_lower = request.lower().strip()
            
            # Route to appropriate handler based on request content
            if any(keyword in request_lower for keyword in ["appointment", "cita", "consulta"]):
                return await self._handle_appointment_request(request, user_context)
            elif any(keyword in request_lower for keyword in ["doctor", "médico", "especialista"]):
                return await self._handle_doctor_request(request, user_context)
            elif any(keyword in request_lower for keyword in ["schedule", "horario", "turno"]):
                return await self._handle_schedule_request(request, user_context)
            elif any(keyword in request_lower for keyword in ["report", "reporte", "análisis"]):
                return await self._handle_report_request(request, user_context)
            elif any(keyword in request_lower for keyword in ["notification", "notificación", "email"]):
                return await self._handle_notification_request(request, user_context)
            else:
                return await self._handle_general_request(request, user_context)
                
        except Exception as e:
            console.print_exception(show_locals=True)
            return {
                "success": False,
                "message": f"Error processing request: {str(e)}",
                "type": "error"
            }
    
    async def _handle_appointment_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle appointment-related requests."""
        global _model
        
        with Session(engine) as session:
            try:
                # Extract intent from request
                if "create" in request.lower() or "agendar" in request.lower():
                    if _model is None:
                        # Model not available — return a helpful response without blocking
                        return {
                            "success": False,
                            "messages": [{
                                "role":"assistant", 
                                "content": "AI model unavailable. Please try again later or contact the administrator."
                                }],
                            "type": "ai_unavailable",
                        }

                    try:
                        response = await self._generate_response(request, user_context)
                        
                        return {
                            "success": True,
                            "messages": response,
                            "type": "appointment_creation",
                            "required_fields": ["doctor_id", "date", "time"],
                            "suggestions": await self._get_available_doctors(session),
                        }
                    except Exception as e:
                        console.print_exception(show_locals=False)
                        return {
                            "success": False,
                            "messages": [{
                                "role":"assistant",
                                "content": f"Error generating AI response: {str(e)}"
                                }],
                            "type": "error",
                        }
                elif "list" in request.lower() or "mostrar" in request.lower():
                    if user_context and user_context.get("user_id"):
                        appointments = await self._get_user_appointments(session, user_context["user_id"])
                        return {
                            "success": True,
                            "messages": [{
                                "role":"assistant",
                                "content":f"Found {len(appointments)} appointments for you."
                                }],
                            "type": "appointment_list",
                            "data": appointments
                        }
                        
                response = await self._generate_response(request, user_context)
                
                return {
                    "success": True,
                    "messages": response,
                    "type": "appointment_help"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "messages": [{
                        "role":"assistant",
                        "content": f"Error handling appointment request: {str(e)}"
                        }],
                    "type": "error"
                }
    
    async def _handle_doctor_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle doctor-related requests."""
        global _model
        if _model is None:
            # Model not available — return a helpful response without blocking
            return {
                "success": False,
                "messages": [{
                    "role":"assistant",
                    "content": "AI model unavailable. Please try again later or contact the administrator."
                    }],
                "type": "ai_unavailable",
            }
        
        with Session(engine) as session:
            try:
                doctors = await self.doctor_repo.get_doctors(session)
                
                if "list" in request.lower() or "mostrar" in request.lower():
                    doctor_list = [
                        {
                           "id": str(doctor.id), 
                           "name": doctor.name, 
                           "specialty": doctor.specialty
                        }
                         for doctor in doctors
                    ]
                    
                    request += "\n\n##Request Context" + f"\n\nFound {len(doctors)} doctors in the system." + "\n\n##Doctor List Context: " + json.dumps(doctor_list)
                    
                    response = await self._generate_response(request, user_context)
                    
                    return {
                        "success": True,
                        "messages": response, 
                        "type": "doctor_list",
                        "data": doctor_list
                    }
                    
                elif "available" in request.lower() or "disponible" in request.lower():
                    available_doctors = await self._get_available_doctors(session)
                    
                    doctor_list = [
                        {
                           "id": str(doctor.id), 
                           "name": doctor.name, 
                           "specialty": doctor.specialty
                        }
                         for doctor in available_doctors
                    ]
                    
                    request += "\n\n##Request Context" + f"\n\nFound {len(available_doctors)} doctors with available appointments." + "\n\n##Doctor List Context: " + json.dumps(doctor_list)
                    
                    response = await self._generate_response(request, user_context)
                    
                    return {
                        "success": True,
                        "messages": response,
                        "type": "available_doctors",
                        "data": available_doctors
                    }
                    
                response = await self._generate_response(request, user_context)
                
                return {
                    "success": True,
                    "messages": response,
                    "type": "doctor_help"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "messages": [{
                        "role":"assistant",
                        "content": f"Error handling doctor request: {str(e)}"
                        }],
                    "type": "error"
                }
    
    async def _handle_schedule_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle schedule-related requests."""
        with Session(engine) as session:
            try:
                
                response = await self._generate_response(request, user_context)
                
                return {
                    "success": True,
                    "messages": response,
                    "type": "schedule_help",
                    "available_actions": ["view_schedule", "create_turn", "modify_schedule"]
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "messages": f"Error handling schedule request: {str(e)}",
                    "type": "error"
                }
    
    async def _handle_report_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle report generation requests."""
        try:
            
            response = await self._generate_response(request, user_context)
            
            return {
                "success": True,
                "messages": response,
                "type": "report_help",
                "available_reports": [
                    "doctor_metrics",
                    "appointment_statistics", 
                    "patient_summary",
                    "schedule_analysis"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "messages": [{
                    "role":"assistant",
                    "content": f"Error handling report request: {str(e)}"
                    }],
                "type": "error"
            }
    
    async def _handle_notification_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle notification and email requests."""
        try:
            
            response = await self._generate_response(request, user_context)
            
            return {
                "success": True,
                "messages": response,
                "type": "notification_help",
                "available_actions": [
                    "send_appointment_reminder",
                    "notify_schedule_change",
                    "send_custom_notification"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "messages": [{
                    "role":"assistant",
                    "content": f"Error handling notification request: {str(e)}"
                    }],
                "type": "error"
            }
    
    async def _handle_general_request(self, request: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle general requests that don't fit specific categories."""
        try:
            response = await self._generate_response(request, user_context)
            
            return {
                "success": True,
                "messages": response,
                "type": "general_help",
                "capabilities": self.model_config["capabilities"]
            }
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return {
                "success": False,
                "messages": [{
                    "role":"assistant",
                    "content":f"Error processing general request: {str(e)}"
                    }],
                "type": "error"
            }
    
    async def _get_available_doctors(self, session: Session) -> List[Dict[str, Any]]:
        """Get list of doctors with their availability status."""
        try:
            doctors = await self.doctor_repo.get_doctors(session)
            available_doctors = []
            
            for doctor in doctors:
                # Here you would check actual availability logic
                available_doctors.append({
                    "id": str(doctor.id),
                    "name": doctor.name,
                    "specialty": getattr(doctor, 'specialty', 'General'),
                    "available_slots": "Available" # This would be calculated from actual schedule
                })
            
            return available_doctors
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return []
    
    async def _get_user_appointments(self, session: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a specific user."""
        try:
            # This would use the actual appointment repository methods
            # For now, returning a placeholder structure
            return [
                {
                    "id": "placeholder",
                    "doctor": "Dr. Example",
                    "date": "2024-01-15",
                    "time": "10:00",
                    "status": "scheduled"
                }
            ]
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return []
    
    async def generate_smart_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate intelligent suggestions based on current context.
        
        Args:
            context: Current system context and user state
            
        Returns:
            List of suggested actions or information
        """
        suggestions = []
        
        try:
            # Time-based suggestions
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 17:  # Business hours
                suggestions.append({
                    "type": "time_based",
                    "message": "It's a good time to schedule appointments or check doctor availability.",
                    "action": "check_availability"
                })
            
            # Context-based suggestions
            if context.get("user_role") == "patient":
                suggestions.append({
                    "type": "role_based",
                    "message": "You can view your upcoming appointments or schedule a new one.",
                    "action": "manage_appointments"
                })
            elif context.get("user_role") == "doctor":
                suggestions.append({
                    "type": "role_based", 
                    "message": "Check your schedule or view patient metrics.",
                    "action": "doctor_dashboard"
                })
            
            return suggestions
            
        except Exception as e:
            console.print_exception(show_locals=True)
            return []
    
    def get_ai_capabilities(self) -> Dict[str, Any]:
        """Return the current AI model capabilities and configuration."""
        return {
            "model": self.model_config,
            "interfaces_available": [
                "UserRepository",
                "DoctorRepository", 
                "TurnAndAppointmentRepository",
                "EmailService"
            ],
            "features": [
                "Natural language processing",
                "Smart suggestions",
                "Cross-system integration",
                "Automated workflows",
                "Intelligent routing"
            ]
        }
    
    async def execute_ai_workflow(self, workflow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute predefined AI workflows that combine multiple system operations.
        
        Args:
            workflow_name: Name of the workflow to execute
            parameters: Parameters needed for the workflow
            
        Returns:
            Result of the workflow execution
        """
        try:
            if workflow_name == "smart_appointment_booking":
                return await self._workflow_smart_appointment_booking(parameters)
            elif workflow_name == "doctor_recommendation":
                return await self._workflow_doctor_recommendation(parameters)
            elif workflow_name == "schedule_optimization":
                return await self._workflow_schedule_optimization(parameters)
            else:
                raise AIAssistantCapabilityError(f"Workflow '{workflow_name}' not supported")
                
        except Exception as e:
            console.print_exception(show_locals=True)
            return {
                "success": False,
                "message": f"Error executing workflow: {str(e)}",
                "workflow": workflow_name
            }
    
    async def _workflow_smart_appointment_booking(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Smart appointment booking workflow with AI optimization."""
        # This would implement intelligent appointment booking
        # considering doctor availability, patient preferences, etc.
        return {
            "success": True,
            "message": "Smart appointment booking workflow completed",
            "type": "workflow_result"
        }
    
    async def _workflow_doctor_recommendation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered doctor recommendation based on patient needs."""
        # This would implement intelligent doctor matching
        return {
            "success": True,
            "message": "Doctor recommendation workflow completed",
            "type": "workflow_result"
        }
    
    async def _workflow_schedule_optimization(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered schedule optimization workflow."""
        # This would implement intelligent schedule optimization
        return {
            "success": True,
            "message": "Schedule optimization workflow completed", 
            "type": "workflow_result"
        }