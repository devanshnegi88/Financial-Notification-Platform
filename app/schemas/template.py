from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from app.core.constants import FinancialEventType, NotificationChannel


class TemplateCreate(BaseModel):
    name: str
    event_type: FinancialEventType
    channel: NotificationChannel
    locale: str = "en"
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    html_body: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    event_type: FinancialEventType
    channel: NotificationChannel
    locale: str
    subject: Optional[str]
    body: str
    html_body: Optional[str]
    variables: Optional[Dict[str, Any]]
    is_active: bool
    version: int
    description: Optional[str]

    model_config = {"from_attributes": True}


class TemplateRenderRequest(BaseModel):
    template_id: UUID
    variables: Dict[str, Any]
