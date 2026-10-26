from pydantic import BaseModel, ConfigDict
from typing import Optional


class SmsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    otp: str


class UserPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    phone: str
    id: Optional[str] = None
    email: Optional[str] = None


class HookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user: UserPayload
    sms: SmsPayload
