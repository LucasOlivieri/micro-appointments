from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    user_id: str = Field(description="The ID of the user who owns the appointment")
    appointment_type: str = Field(min_length=1, description="Appointment type name")
    start: datetime = Field(description="Appointment start, preferably with a timezone")
    name: str = Field(min_length=1, description="Customer name")
    phone: str = Field(min_length=1, description="Customer phone number")


class AppointmentUpdate(BaseModel):
    user_id: str = Field(description="The ID of the user who owns the appointment")
    appointment_type: str | None = Field(default=None, min_length=1)
    start: datetime | None = None


class Appointment(BaseModel):
    id: int
    user: str
    reason: str
    start: str
    end: str
    appointment_type: str
    name: str | None = None
    phone: str | None = None


class AvailableSlot(BaseModel):
    start: str
    end: str
    appointment_type: str


class AvailableAppointmentType(BaseModel):
    name: str
    duration_minutes: int


class User(BaseModel):
    id: str
    name: str
    timezone: str

class UserOut(BaseModel):
    id: str
    name: str
    timezone: str
    available_appointment_types: List[AvailableAppointmentType]
