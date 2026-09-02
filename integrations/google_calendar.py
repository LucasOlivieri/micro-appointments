"""Google Calendar integration for booked appointments.

Uses Google OAuth 2.0 (desktop flow) to create, update, and delete calendar
events whenever a booked blocked_time record is created, updated, or deleted.
The doctor's email is added as an event attendee.

On first run, the integration will print a URL to visit for authorization.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.models import BlockedTime, User
from core.services.appointments import CREATED, DELETED, UPDATED, onaction
from integrations.base import Integration
from integrations.factory import IntegrationFactory

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "primary"


def _load_or_authenticate_credentials(
    client_secret_path: str, token_path: str
) -> Credentials:
    """Load saved token or run the OAuth desktop flow to get one."""
    token_path_obj = Path(token_path)
    if token_path_obj.exists():
        creds = Credentials.from_authorized_user_file(str(token_path_obj), SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            _save_token(creds, token_path_obj)
            return creds

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path_obj)
    return creds


def _save_token(creds: Credentials, token_path: Path) -> None:
    """Persist credentials to disk so we don't re-auth every time."""
    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("OAuth token saved to %s", token_path)


@IntegrationFactory.register
class GoogleCalendarIntegration(Integration):
    """Sync booked appointments to Google Calendar via OAuth 2.0."""

    name = "google_calendar"
    required_env_vars = ("GOOGLE_OAUTH_CLIENT_SECRET",)

    def __init__(self, environ: Mapping[str, str]):
        super().__init__(environ)
        client_secret_path = environ["GOOGLE_OAUTH_CLIENT_SECRET"]
        token_path = environ.get("GOOGLE_TOKEN_FILE", "google_token.json")
        credentials = _load_or_authenticate_credentials(client_secret_path, token_path)
        self.service = build("calendar", "v3", credentials=credentials)
        self._db_path = Path(__file__).resolve().parent.parent / "db.sqlite3"
        self._register_handlers()

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> GoogleCalendarIntegration:
        cls.validate_env(environ)
        return cls(environ)

    def _register_handlers(self) -> None:
        @onaction(CREATED)
        async def handle_created(item: dict) -> None:
            await self._sync_created(item)

        @onaction(UPDATED)
        async def handle_updated(item: dict) -> None:
            await self._sync_updated(item)

        @onaction(DELETED)
        async def handle_deleted(item: dict) -> None:
            await self._sync_deleted(item)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_user_email(self, user_id: str) -> str | None:
        """Return the email for *user_id* from the users table."""
        try:
            row = await User.filter(id=user_id).first()
            return row.email if row else None
        except Exception:
            logger.exception("Failed to look up email for user %s", user_id)
            return None

    async def _get_user_timezone(self, user_id: str) -> str | None:
        """Return the timezone for *user_id* from the users table."""
        try:
            row = await User.filter(id=user_id).first()
            return row.timezone if row else None
        except Exception:
            logger.exception("Failed to look up timezone for user %s", user_id)
            return None

    async def _store_event_id(self, blocked_time_id: int, event_id: str) -> None:
        """Persist the Google Calendar event ID on the blocked_times row."""
        try:
            await BlockedTime.filter(id=blocked_time_id).update(
                google_event_id=event_id
            )
        except Exception:
            logger.exception(
                "Failed to store google_event_id for blocked_time %s",
                blocked_time_id,
            )

    async def _get_event_id(self, blocked_time_id: int) -> str | None:
        """Retrieve the stored Google Calendar event ID for a blocked_time row."""
        try:
            row = await BlockedTime.filter(id=blocked_time_id).first()
            return row.google_event_id if row else None
        except Exception:
            logger.exception(
                "Failed to read google_event_id for blocked_time %s",
                blocked_time_id,
            )
            return None

    # ------------------------------------------------------------------
    # Event sync handlers
    # ------------------------------------------------------------------

    async def _sync_created(self, item: dict) -> None:
        """Create a Google Calendar event for a newly booked appointment."""
        if item.get("reason") != "booked":
            return

        user_id = cast(str, item.get("user"))
        user_email = await self._get_user_email(user_id)
        if not user_email:
            logger.warning(
                "Cannot create calendar event for user %s: no email found", user_id
            )
            return

        timezone = await self._get_user_timezone(user_id) or "UTC"
        summary = item.get("appointment_type", "Appointment")
        start_str = item.get("start", "")
        end_str = item.get("end", "")

        if not start_str or not end_str:
            logger.warning("Skipping calendar event: missing start or end")
            return

        event_body = {
            "summary": summary,
            "start": {"dateTime": start_str, "timeZone": timezone},
            "end": {"dateTime": end_str, "timeZone": timezone},
            "attendees": [{"email": user_email}],
        }

        try:
            created = (
                self.service.events()
                .insert(calendarId=CALENDAR_ID, body=event_body)
                .execute()
            )
            event_id = created["id"]
            logger.info(
                "Created calendar event %s for blocked_time %s",
                event_id,
                item.get("id"),
            )
            await self._store_event_id(item["id"], event_id)
        except (HttpError, GoogleAuthError) as error:
            logger.error(
                "Failed to create calendar event for blocked_time %s: %s",
                item.get("id"),
                error,
            )

    async def _sync_updated(self, item: dict) -> None:
        """Update a Google Calendar event when a booked appointment changes."""
        if item.get("reason") != "booked":
            return

        blocked_time_id = cast(int, item.get("id"))
        event_id = item.get("google_event_id") or await self._get_event_id(
            blocked_time_id
        )

        if not event_id:
            logger.info(
                "No google_event_id for blocked_time %s — creating new event",
                blocked_time_id,
            )
            await self._sync_created(item)
            return

        user_id = cast(str, item.get("user"))
        timezone = await self._get_user_timezone(user_id) or "UTC"
        start_str = item.get("start", "")
        end_str = item.get("end", "")

        if not start_str or not end_str:
            logger.warning("Skipping calendar event update: missing start or end")
            return

        try:
            existing = (
                self.service.events()
                .get(calendarId=CALENDAR_ID, eventId=event_id)
                .execute()
            )
            existing["start"] = {"dateTime": start_str, "timeZone": timezone}
            existing["end"] = {"dateTime": end_str, "timeZone": timezone}
            self.service.events().update(
                calendarId=CALENDAR_ID, eventId=event_id, body=existing
            ).execute()
            logger.info(
                "Updated calendar event %s for blocked_time %s",
                event_id,
                blocked_time_id,
            )
        except HttpError as error:
            if error.status_code == 410:
                logger.info(
                    "Event %s is gone (410), creating replacement for blocked_time %s",
                    event_id,
                    blocked_time_id,
                )
                await self._sync_created(item)
            else:
                logger.error(
                    "Failed to update calendar event %s for blocked_time %s: %s",
                    event_id,
                    blocked_time_id,
                    error,
                )
        except GoogleAuthError as error:
            logger.error(
                "Auth error updating calendar event %s for blocked_time %s: %s",
                event_id,
                blocked_time_id,
                error,
            )

    async def _sync_deleted(self, item: dict) -> None:
        """Delete a Google Calendar event when a booked appointment is cancelled."""
        if item.get("reason") != "booked":
            return

        blocked_time_id = cast(int, item.get("id"))
        event_id = item.get("google_event_id") or await self._get_event_id(
            blocked_time_id
        )

        if not event_id:
            logger.debug(
                "No google_event_id for blocked_time %s — nothing to delete",
                blocked_time_id,
            )
            return

        try:
            self.service.events().delete(
                calendarId=CALENDAR_ID, eventId=event_id
            ).execute()
            logger.info(
                "Deleted calendar event %s for blocked_time %s",
                event_id,
                blocked_time_id,
            )
        except HttpError as error:
            if error.status_code == 404:
                logger.debug(
                    "Event %s already deleted (404) for blocked_time %s",
                    event_id,
                    blocked_time_id,
                )
            else:
                logger.error(
                    "Failed to delete calendar event %s for blocked_time %s: %s",
                    event_id,
                    blocked_time_id,
                    error,
                )
        except GoogleAuthError as error:
            logger.error(
                "Auth error deleting calendar event %s for blocked_time %s: %s",
                event_id,
                blocked_time_id,
                error,
            )

    # ------------------------------------------------------------------
    # Lifecycle (no long-running process needed)
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """No-op: handlers fire synchronously via _dispatch."""
        logger.info("Google Calendar integration enabled.")

    async def stop(self) -> None:
        """No-op: no resources to release."""
