from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.constants import FinancialEventType


class UserPreferenceResponse(BaseModel):
    id: UUID
    user_id: UUID
    sms_enabled: bool
    email_enabled: bool
    whatsapp_enabled: bool
    push_enabled: bool
    in_app_enabled: bool
    disabled_event_types: Optional[str]
    quiet_hours_enabled: bool
    quiet_hours_start: int
    quiet_hours_end: int
    frequency_cap_hourly: int
    frequency_cap_daily: int
    frequency_cap_weekly: int
    preferred_locale: str

    model_config = {"from_attributes": True}


class UserPreferenceUpdate(BaseModel):
    sms_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    disabled_event_types: Optional[List[FinancialEventType]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = Field(default=None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(default=None, ge=0, le=23)
    frequency_cap_hourly: Optional[int] = Field(default=None, ge=0)
    frequency_cap_daily: Optional[int] = Field(default=None, ge=0)
    frequency_cap_weekly: Optional[int] = Field(default=None, ge=0)
    preferred_locale: Optional[str] = None
