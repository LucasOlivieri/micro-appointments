from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    id: str
    name: str
    email: str | None = None
    message: str | None = None
    system_prompt: str | None = None
    timezone: str = "America/Argentina/Buenos_Aires"


@dataclass
class Rule:
    id: int = 0
    user_id: str = ""
    weekday: int | None = None
    start: str = ""
    end: str = ""
    rrule: str | None = None
    dtstart: str | None = None
    exclude_dates: list[str] | None = None


@dataclass
class AppointmentType:
    id: int = 0
    user_id: str = ""
    name: str = ""
    duration_minutes: int = 0
    advance_notice_minutes: int | None = None


@dataclass
class Customer:
    id: str = ""
    phone: str = ""
    name: str = ""
    info: str | None = None


@dataclass
class BlockedTime:
    id: int = 0
    user_id: str = ""
    reason: str = ""
    start: str = ""
    end: str = ""
    appointment_type: str | None = None
    customer: str | None = None
    google_event_id: str | None = None


@dataclass
class SchemaMigration:
    id: int = 0
    name: str = ""
