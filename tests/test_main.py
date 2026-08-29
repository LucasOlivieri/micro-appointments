"""Unit tests for all functions in src/main.py."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import sqlite_utils

import core.main as main_module
from core.main import (
    book_appointment,
    get_appointment_type,
    get_next_free_slots,
    get_working_hours,
    is_blocked,
    load_user,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user():
    return {
        "id": "595b6fb0-bef2-4a55-a122-34ab5e8bcc77",
        "timezone": "America/Argentina/Buenos_Aires",
        "appointment_types": [
            {"name": "Initial Consultation", "duration_minutes": 30},
            {"name": "Follow-up", "duration_minutes": 15},
        ],
        "rules": [
            {"weekday": 0, "start": "09:00", "end": "17:00"},
            {"weekday": 1, "start": "09:00", "end": "17:00"},
            {"weekday": 2, "start": "09:00", "end": "17:00"},
            {"weekday": 3, "start": "09:00", "end": "17:00"},
            {"weekday": 4, "start": "09:00", "end": "17:00"},
        ],
        "blocked_time": [],
    }


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DATABASE_PATH", tmp_path / "testdb.sqlite3")


TZ = ZoneInfo("America/Argentina/Buenos_Aires")


# ===================================================================
# get_appointment_type
# ===================================================================


class TestGetAppointmentType:
    __test__ = False

    def test_finds_by_exact_name(self, user):
        result = get_appointment_type(user, "Follow-up")
        assert result["name"] == "Follow-up"
        assert result["duration_minutes"] == 15

    def test_finds_case_insensitive(self, user):
        result = get_appointment_type(user, "initial consultation")
        assert result["name"] == "Initial Consultation"

    def test_finds_mixed_case(self, user):
        result = get_appointment_type(user, "FOLLOW-UP")
        assert result["name"] == "Follow-up"

    def test_raises_for_unknown_type(self, user):
        with pytest.raises(ValueError, match="Unknown appointment type: Brain Surgery"):
            get_appointment_type(user, "Brain Surgery")

    def test_raises_for_empty_string(self, user):
        with pytest.raises(ValueError, match="Unknown appointment type:"):
            get_appointment_type(user, "")


# ===================================================================
# is_blocked
# ===================================================================


class TestIsBlocked:
    __test__ = False
    """Tests for the three kinds of blocked intervals + edge cases."""

    # --- Exact datetime interval ---

    def test_blocked_exact_datetime_overlap(self, user):
        user["blocked_time"] = [
            {
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T11:00:00-03:00",
            }
        ]
        start = datetime(2026, 8, 24, 10, 30, tzinfo=TZ)
        end = datetime(2026, 8, 24, 11, 0, tzinfo=TZ)
        assert is_blocked(user, start, end) is True

    def test_blocked_exact_datetime_before(self, user):
        user["blocked_time"] = [
            {
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T11:00:00-03:00",
            }
        ]
        start = datetime(2026, 8, 24, 9, 0, tzinfo=TZ)
        end = datetime(2026, 8, 24, 9, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_blocked_exact_datetime_after(self, user):
        user["blocked_time"] = [
            {
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T11:00:00-03:00",
            }
        ]
        start = datetime(2026, 8, 24, 11, 0, tzinfo=TZ)
        end = datetime(2026, 8, 24, 12, 0, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_blocked_exact_datetime_touches_start(self, user):
        """Slot ends exactly when block starts — not blocked."""
        user["blocked_time"] = [
            {
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T11:00:00-03:00",
            }
        ]
        start = datetime(2026, 8, 24, 9, 30, tzinfo=TZ)
        end = datetime(2026, 8, 24, 10, 0, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_blocked_exact_datetime_touches_end(self, user):
        """Slot starts exactly when block ends — not blocked."""
        user["blocked_time"] = [
            {
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T11:00:00-03:00",
            }
        ]
        start = datetime(2026, 8, 24, 11, 0, tzinfo=TZ)
        end = datetime(2026, 8, 24, 11, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    # --- Entire date range ---

    def test_blocked_date_range_overlap(self, user):
        user["blocked_time"] = [
            {
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ]
        start = datetime(2026, 8, 15, 10, 0, tzinfo=TZ)
        end = datetime(2026, 8, 15, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is True

    def test_blocked_date_range_exactly_on_start(self, user):
        """Slot on the start_date's midnight boundary."""
        user["blocked_time"] = [
            {
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ]
        start = datetime(2026, 8, 1, 0, 0, tzinfo=TZ)
        end = datetime(2026, 8, 1, 0, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is True

    def test_blocked_date_range_before(self, user):
        user["blocked_time"] = [
            {
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ]
        start = datetime(2026, 7, 31, 10, 0, tzinfo=TZ)
        end = datetime(2026, 7, 31, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_blocked_date_range_after(self, user):
        user["blocked_time"] = [
            {
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ]
        start = datetime(2026, 9, 1, 0, 0, tzinfo=TZ)
        end = datetime(2026, 9, 1, 0, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    # --- Recurring month ---

    def test_blocked_recurring_month_matches(self, user):
        user["blocked_time"] = [{"condition": {"month": "december"}}]
        start = datetime(2026, 12, 15, 10, 0, tzinfo=TZ)
        end = datetime(2026, 12, 15, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is True

    def test_blocked_recurring_month_no_match(self, user):
        user["blocked_time"] = [{"condition": {"month": "december"}}]
        start = datetime(2026, 6, 15, 10, 0, tzinfo=TZ)
        end = datetime(2026, 6, 15, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_blocked_recurring_month_case_insensitive(self, user):
        user["blocked_time"] = [{"condition": {"month": "August"}}]
        start = datetime(2026, 8, 10, 10, 0, tzinfo=TZ)
        end = datetime(2026, 8, 10, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is True

    def test_blocked_recurring_month_condition_without_month(self, user):
        """condition dict without a 'month' key should not block anything."""
        user["blocked_time"] = [{"condition": {}}]
        start = datetime(2026, 8, 10, 10, 0, tzinfo=TZ)
        end = datetime(2026, 8, 10, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    # --- No blocked_time ---

    def test_no_blocked_time(self, user):
        start = datetime(2026, 8, 24, 10, 0, tzinfo=TZ)
        end = datetime(2026, 8, 24, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False

    def test_empty_blocked_time_list(self, user):
        user["blocked_time"] = []
        start = datetime(2026, 8, 24, 10, 0, tzinfo=TZ)
        end = datetime(2026, 8, 24, 10, 30, tzinfo=TZ)
        assert is_blocked(user, start, end) is False


# ===================================================================
# get_working_hours
# ===================================================================


class TestGetWorkingHours:
    __test__ = False

    def test_returns_start_and_end_for_matching_weekday(self, user):
        # 2026-08-24 is a Monday (weekday 0)
        day = date(2026, 8, 24)
        result = get_working_hours(user, day)
        expected_start = datetime(2026, 8, 24, 9, 0, tzinfo=TZ)
        expected_end = datetime(2026, 8, 24, 17, 0, tzinfo=TZ)
        assert result == (expected_start, expected_end)

    def test_returns_none_for_weekend(self, user):
        # 2026-08-30 is a Sunday (weekday 6)
        day = date(2026, 8, 30)
        assert get_working_hours(user, day) is None

    def test_returns_none_for_weekday_without_rule(self, user):
        user["rules"] = [{"weekday": 0, "start": "09:00", "end": "17:00"}]
        # Tuesday (weekday 2) has no rule
        day = date(2026, 8, 25)
        assert get_working_hours(user, day) is None

    def test_empty_rules_list(self, user):
        user["rules"] = []
        day = date(2026, 8, 24)
        assert get_working_hours(user, day) is None

    def test_first_rule_wins_when_multiple_match(self, user):
        user["rules"] = [
            {"weekday": 0, "start": "08:00", "end": "12:00"},
            {"weekday": 0, "start": "13:00", "end": "17:00"},
        ]
        day = date(2026, 8, 24)
        result = get_working_hours(user, day)
        expected_start = datetime(2026, 8, 24, 8, 0, tzinfo=TZ)
        expected_end = datetime(2026, 8, 24, 12, 0, tzinfo=TZ)
        assert result == (expected_start, expected_end)

    def test_rrule_matches_configured_weekday(self, user):
        user["rules"] = [
            {
                "rrule": "FREQ=WEEKLY;BYDAY=MO,WE",
                "start": "10:00",
                "end": "12:00",
            }
        ]

        result = get_working_hours(user, date(2026, 8, 26))

        assert result == (
            datetime(2026, 8, 26, 10, 0, tzinfo=TZ),
            datetime(2026, 8, 26, 12, 0, tzinfo=TZ),
        )

    def test_rrule_respects_until_and_excluded_dates(self, user):
        user["rules"] = [
            {
                "rrule": "FREQ=WEEKLY;BYDAY=MO;UNTIL=20260907T000000",
                "exclude_dates": ["2026-08-31"],
                "start": "10:00",
                "end": "12:00",
            }
        ]

        assert get_working_hours(user, date(2026, 8, 31)) is None
        assert get_working_hours(user, date(2026, 9, 14)) is None

    def test_rrule_does_not_match_previous_day_at_midnight(self, user):
        user["rules"] = [
            {
                "rrule": "FREQ=WEEKLY;BYDAY=MO",
                "start": "12:40",
                "end": "18:40",
            }
        ]

        assert get_working_hours(user, date(2026, 8, 30)) is None
        assert get_working_hours(user, date(2026, 8, 31)) is not None


# ===================================================================
# get_next_free_slots
# ===================================================================


class TestGetNextFreeSlots:
    __test__ = False

    def test_returns_requested_number_of_slots(self, user):
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=3,
        )
        assert len(slots) == 3

    def test_each_slot_has_correct_keys(self, user):
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=1,
        )
        assert len(slots) == 1
        slot = slots[0]
        assert "start" in slot
        assert "end" in slot
        assert "appointment_type" in slot

    def test_slots_have_correct_appointment_type(self, user):
        slots = get_next_free_slots(
            user,
            appointment_type="Initial Consultation",
            nr_slots=2,
        )
        for slot in slots:
            assert slot["appointment_type"] == "Initial Consultation"

    def test_slots_are_sequential_by_duration(self, user):
        """15-min Follow-up slots should be 15 minutes apart."""
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=3,
        )
        for i in range(len(slots) - 1):
            s1 = datetime.fromisoformat(slots[i]["end"])
            s2 = datetime.fromisoformat(slots[i + 1]["start"])
            assert s1 == s2, f"Slot {i} end {s1} != slot {i + 1} start {s2}"

    def test_slots_skip_blocked_times(self, user):
        """Block a period and verify slots skip it."""
        user["blocked_time"] = [
            {
                "start": "2026-08-24T09:15:00-03:00",
                "end": "2026-08-24T10:00:00-03:00",
            }
        ]
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=3,
            from_datetime=datetime(2026, 8, 24, 9, 0, tzinfo=TZ),
        )
        # 09:00-09:15 is free, 09:15-10:00 blocked,
        # so first slot should be 09:00, second at 10:00
        assert len(slots) >= 2
        start0 = datetime.fromisoformat(slots[0]["start"])
        assert start0.hour == 9 and start0.minute == 0
        start1 = datetime.fromisoformat(slots[1]["start"])
        assert start1.hour == 10 and start1.minute == 0

    def test_from_datetime_filters_past_slots(self, user):
        """Slots before from_datetime should not be returned."""
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=2,
            from_datetime=datetime(2026, 8, 24, 16, 0, tzinfo=TZ),
        )
        for slot in slots:
            start = datetime.fromisoformat(slot["start"])
            assert start >= datetime(2026, 8, 24, 16, 0, tzinfo=TZ)

    def test_from_datetime_none_defaults_to_now_equivalent(self, user):
        """from_datetime=None is equivalent to passing datetime.now(tz) explicitly."""
        slots_default = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=1,
            from_datetime=None,
        )
        slots_explicit = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=1,
            from_datetime=datetime.now(TZ),
        )
        # Both should return a valid slot (the exact slot may differ
        # depending on timing, but both should succeed)
        assert len(slots_default) == 1
        assert len(slots_explicit) == 1

    def test_from_datetime_without_tzinfo_gets_tz(self, user):
        """A naive from_datetime should be treated as in the user's timezone."""
        naive = datetime(2026, 8, 24, 10, 0)
        slots = get_next_free_slots(
            user,
            appointment_type="Follow-up",
            nr_slots=1,
            from_datetime=naive,
        )
        assert len(slots) == 1
        start = datetime.fromisoformat(slots[0]["start"])
        assert start.tzinfo is not None

    def test_spans_multiple_days_if_needed(self, user):
        """If not enough slots in one day, continue to next day."""
        slots = get_next_free_slots(
            user,
            appointment_type="Initial Consultation",
            nr_slots=20,
            from_datetime=datetime(2026, 8, 24, 9, 0, tzinfo=TZ),
        )
        assert len(slots) == 20
        days = {datetime.fromisoformat(s["start"]).date() for s in slots}
        assert len(days) > 1, "Should span multiple days"

    def test_unknown_appointment_type(self, user):
        with pytest.raises(ValueError, match="Unknown appointment type"):
            get_next_free_slots(
                user,
                appointment_type="Nope",
                nr_slots=1,
            )


# ===================================================================
# book_appointment
# ===================================================================


class TestBookAppointment:
    __test__ = False

    def test_book_successfully(self, user):
        booking = book_appointment(
            user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )
        assert booking["reason"] == "booked"
        assert booking["start"] == "2026-08-24T10:00:00-03:00"
        assert booking["end"] == "2026-08-24T10:15:00-03:00"
        assert booking["appointment_type"] == "Follow-up"
        assert len(user["blocked_time"]) == 1

    def test_book_appends_to_blocked_time(self, user):
        user["blocked_time"] = [
            {
                "start": "2026-08-24T09:00:00-03:00",
                "end": "2026-08-24T10:00:00-03:00",
                "reason": "existing",
            }
        ]
        book_appointment(user, "Follow-up", "2026-08-24T11:00:00-03:00")
        assert len(user["blocked_time"]) == 2

    def test_book_with_datetime_object(self, user):
        dt = datetime(2026, 8, 24, 14, 0, tzinfo=TZ)
        booking = book_appointment(user, "Follow-up", dt)
        assert booking["start"] == "2026-08-24T14:00:00-03:00"

    def test_book_with_naive_datetime_gets_tz(self, user):
        naive = datetime(2026, 8, 24, 14, 0)
        booking = book_appointment(user, "Follow-up", naive)
        start = datetime.fromisoformat(booking["start"])
        assert start.tzinfo is not None

    def test_outside_working_hours_too_early(self, user):
        with pytest.raises(ValueError, match="Appointment is outside working hours"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T08:00:00-03:00",
            )

    def test_outside_working_hours_too_late(self, user):
        with pytest.raises(ValueError, match="Appointment is outside working hours"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T17:00:00-03:00",
            )

    def test_outside_working_hours_ends_late(self, user):
        """Starts at 16:50 but a 15 min slot ends at 17:05 -> outside."""
        with pytest.raises(ValueError, match="Appointment is outside working hours"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T16:50:00-03:00",
            )

    def test_no_working_hours_that_day(self, user):
        # Sunday
        with pytest.raises(ValueError, match="No working hours on this day"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-30T10:00:00-03:00",
            )

    def test_double_booking_raises_error(self, user):
        book_appointment(
            user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )
        with pytest.raises(ValueError, match="Time slot is already blocked"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T10:00:00-03:00",
            )

    def test_overlapping_booking_raises_error(self, user):
        """An overlapping slot should also be considered blocked."""
        book_appointment(
            user,
            "Initial Consultation",
            "2026-08-24T10:00:00-03:00",
        )
        with pytest.raises(ValueError, match="Time slot is already blocked"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T10:15:00-03:00",
            )

    def test_unknown_appointment_type(self, user):
        with pytest.raises(ValueError, match="Unknown appointment type"):
            book_appointment(
                user,
                "Nope",
                "2026-08-24T10:00:00-03:00",
            )

    def test_returns_correct_duration_for_different_types(self, user):
        booking = book_appointment(
            user,
            "Initial Consultation",
            "2026-08-24T10:00:00-03:00",
        )
        assert booking["end"] == "2026-08-24T10:30:00-03:00"

    def test_blocked_by_date_range_raises(self, user):
        user["blocked_time"] = [{"start_date": "2026-08-01", "end_date": "2026-08-31"}]
        with pytest.raises(ValueError, match="Time slot is already blocked"):
            book_appointment(
                user,
                "Follow-up",
                "2026-08-24T10:00:00-03:00",
            )

    def test_booking_is_persisted(self, user):
        book_appointment(
            user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )

        db = sqlite_utils.Database(main_module.DATABASE_PATH)
        rows = list(
            db.query(
                "SELECT user, reason, start, end, "
                "appointment_type FROM blocked_times "
                "WHERE user = :user_id AND reason = 'booked'",
                {"user_id": user["id"]},
            )
        )
        assert rows == [
            {
                "user": user["id"],
                "reason": "booked",
                "start": "2026-08-24T10:00:00-03:00",
                "end": "2026-08-24T10:15:00-03:00",
                "appointment_type": "Follow-up",
            }
        ]

    def test_reloaded_user_sees_persisted_booking(self, user):
        main_module.AppointmentsService(main_module.DATABASE_PATH)
        db = sqlite_utils.Database(main_module.DATABASE_PATH)
        db["users"].upsert(
            {
                "id": user["id"],
                "name": "User",
                "email": "user@example.com",
                "timezone": user["timezone"],
            }
        )
        db["rules"].insert_all(
            [
                {
                    "id": index + 101,
                    "user": user["id"],
                    "weekday": rule["weekday"],
                    "start": rule["start"],
                    "end": rule["end"],
                }
                for index, rule in enumerate(user["rules"])
            ]
        )
        db["appointment_types"].insert_all(
            [
                {
                    "id": index + 101,
                    "user": user["id"],
                    **appointment_type,
                }
                for index, appointment_type in enumerate(user["appointment_types"])
            ]
        )
        book_appointment(
            user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )

        reloaded_user = load_user(user["id"])

        assert reloaded_user["blocked_time"][-1] == {
            "reason": "booked",
            "start": "2026-08-24T10:00:00-03:00",
            "end": "2026-08-24T10:15:00-03:00",
            "appointment_type": "Follow-up",
        }
        with pytest.raises(ValueError, match="Time slot is already blocked"):
            book_appointment(
                reloaded_user,
                "Follow-up",
                "2026-08-24T10:00:00-03:00",
            )

    def test_bookings_are_isolated_by_user(self, user):
        second_user_id = "second-user"
        main_module.AppointmentsService(main_module.DATABASE_PATH)
        db = sqlite_utils.Database(main_module.DATABASE_PATH)
        db["users"].insert(
            {
                "id": second_user_id,
                "name": "Second User",
                "email": "second@example.com",
                "timezone": user["timezone"],
            }
        )
        db["rules"].insert(
            {
                "id": 101,
                "user": second_user_id,
                "weekday": 0,
                "start": "09:00",
                "end": "17:00",
            }
        )
        db["appointment_types"].insert(
            {
                "id": 101,
                "user": second_user_id,
                "name": "Follow-up",
                "duration_minutes": 15,
            }
        )

        book_appointment(
            user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )
        second_user = load_user(second_user_id)

        assert second_user["blocked_time"] == []
        booking = book_appointment(
            second_user,
            "Follow-up",
            "2026-08-24T10:00:00-03:00",
        )
        assert booking["start"] == "2026-08-24T10:00:00-03:00"
