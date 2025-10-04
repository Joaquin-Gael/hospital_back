from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class AIAssistantRequest(BaseModel):
    """Schema for AI assistant requests"""
    request: str
    user_context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AIAssistantResponse(BaseModel):
    """Schema for AI assistant responses"""
    success: bool
    message: str
    type: str
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = datetime.now()


class AIWorkflowRequest(BaseModel):
    """Schema for AI workflow execution requests"""
    workflow_name: str
    parameters: Dict[str, Any]
    user_context: Optional[Dict[str, Any]] = None


class AIWorkflowResponse(BaseModel):
    """Schema for AI workflow execution responses"""
    success: bool
    message: str
    workflow: str
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()


class AICapabilitiesResponse(BaseModel):
    """Schema for AI capabilities response"""
    model: Dict[str, Any]
    interfaces_available: List[str]
    features: List[str]
    workflows: List[str]


class AISuggestionRequest(BaseModel):
    """Schema for AI suggestion requests"""
    context: Dict[str, Any]
    user_role: Optional[str] = None
    current_page: Optional[str] = None


class AISuggestionResponse(BaseModel):
    """Schema for AI suggestions response"""
    suggestions: List[Dict[str, Any]]
    context_analyzed: Dict[str, Any]
    timestamp: datetime = datetime.now()