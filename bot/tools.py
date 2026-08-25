from typing import Any

import httpx
from agents import function_tool


class AppointmentsApiClient:
    """Small async client for the appointments REST API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15) as client:
            response = await client.request(method, path, **kwargs)
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"Appointments API error ({response.status_code}): {detail}")
        return response.json()


def build_tools(api_url: str):
    client = AppointmentsApiClient(api_url)

    @function_tool
    async def find_available_slots(
        user_id: str,
        appointment_type: str,
        nr_slots: int = 5,
        from_datetime: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find available slots for a user and appointment type.

        from_datetime must be an ISO 8601 datetime when provided.
        """
        params: dict[str, Any] = {
            "user_id": user_id,
            "appointment_type": appointment_type,
            "nr_slots": nr_slots,
        }
        if from_datetime is not None:
            params["from_datetime"] = from_datetime
        return await client.request("GET", "/appointments/available-slots", params=params)

    @function_tool
    async def list_user_appointments(
        user_id: str, appointment_type: str | None = None
    ) -> list[dict[str, Any]]:
        """List a user's scheduled appointments, optionally filtered by type."""
        params: dict[str, Any] = {"user_id": user_id}
        if appointment_type is not None:
            params["appointment_type"] = appointment_type
        return await client.request("GET", "/appointments", params=params)

    @function_tool
    async def schedule_appointment(
        user_id: str, appointment_type: str, start: str, name: str, phone: str
    ) -> dict[str, Any]:
        """Schedule an appointment at an ISO 8601 start datetime.

        name and phone are required customer details. Use values already
        provided in the conversation; otherwise ask the user for them before
        calling this tool.
        """
        return await client.request(
            "POST",
            "/appointments",
            json={
                "user_id": user_id,
                "appointment_type": appointment_type,
                "start": start,
                "name": name,
                "phone": phone,
            },
        )

    @function_tool
    async def move_appointment(
        user_id: str,
        appointment_id: int,
        start: str | None = None,
        appointment_type: str | None = None,
    ) -> dict[str, Any]:
        """Move an appointment, optionally changing its type, using an ISO 8601 start datetime."""
        if start is None and appointment_type is None:
            raise ValueError("Provide a new start or appointment type")
        payload: dict[str, Any] = {"user_id": user_id}
        if start is not None:
            payload["start"] = start
        if appointment_type is not None:
            payload["appointment_type"] = appointment_type
        return await client.request("PATCH", f"/appointments/{appointment_id}", json=payload)

    @function_tool
    async def find_available_appointment_types(
        user_id: str,
    ) -> list[dict[str, Any]]:
        """List the appointment types configured for a user's calendar."""
        return await client.request(
            "GET",
            "/appointments/available-types",
            params={"user_id": user_id},
        )

    return [
        find_available_appointment_types,
        find_available_slots,
        list_user_appointments,
        schedule_appointment,
        move_appointment,
    ]