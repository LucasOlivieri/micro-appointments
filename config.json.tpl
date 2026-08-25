{
    "user": {
        "name": $user_name,
        "email": $user_email,
        "timezone": $timezone,
        "id": $user_id,
        "rules": [
            {
                "user": $user_id,
                "id": 1,
                "weekday": 0,
                "start_time": "09:00",
                "end_time": "17:00"
            },
            {
                "user": $user_id,
                "id": 2,
                "weekday": 1,
                "start_time": "09:00",
                "end_time": "17:00"
            },
            {
                "user": $user_id,
                "id": 3,
                "weekday": 2,
                "start_time": "09:00",
                "end_time": "17:00"
            },
            {
                "user": $user_id,
                "id": 4,
                "weekday": 3,
                "start_time": "09:00",
                "end_time": "17:00"
            },
            {
                "user": $user_id,
                "id": 5,
                "weekday": 4,
                "start_time": "09:00",
                "end_time": "17:00"
            }
        ],
        "appointment_types": [
            {
                "user": $user_id,
                "id": 1,
                "name": "Initial Consultation",
                "duration_minutes": 30
            },
            {
                "user": $user_id,
                "id": 2,
                "name": "Follow-up",
                "duration_minutes": 15
            }
        ],
        "blocked_times": [
            {
                "user": $user_id,
                "id": 1,
                "reason": "vacation",
                "start": "2026-07-01T00:00:00-03:00",
                "end": "2026-07-31T00:00:00-03:00"
            },
            {
                "user": $user_id,
                "id": 2,
                "reason": "vacation",
                "start": "2026-02-01T00:00:00-03:00",
                "end": "2026-02-25T00:00:00-03:00"
            }
        ]
    }
}