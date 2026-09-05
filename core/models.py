from tortoise import fields
from tortoise.models import Model


class User(Model):
    id: str = fields.CharField(max_length=128, primary_key=True)  # type: ignore[assignment]
    name: str = fields.CharField(max_length=255)  # type: ignore[assignment]
    email: str | None = fields.CharField(max_length=320, null=True)  # type: ignore[assignment]
    message: str | None = fields.TextField(null=True)  # type: ignore[assignment]
    system_prompt: str | None = fields.TextField(null=True)  # type: ignore[assignment]
    timezone: str = fields.CharField(  # type: ignore[assignment]
        max_length=128, default="America/Argentina/Buenos_Aires"
    )

    class Meta:
        table = "users"


class Rule(Model):
    id: int = fields.IntField(primary_key=True)  # type: ignore[assignment]
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(  # type: ignore[assignment]
        "models.User", related_name="rules", source_field="user"
    )
    user_id: str
    weekday: int | None = fields.IntField(null=True)  # type: ignore[assignment]
    start: str = fields.CharField(max_length=16)  # type: ignore[assignment]
    end: str = fields.CharField(max_length=16)  # type: ignore[assignment]
    rrule: str | None = fields.TextField(null=True)  # type: ignore[assignment]
    dtstart: str | None = fields.CharField(max_length=64, null=True)  # type: ignore[assignment]
    exclude_dates: list[str] | None = fields.JSONField(null=True)  # type: ignore[assignment]

    class Meta:
        table = "rules"


class AppointmentType(Model):
    id: int = fields.IntField(primary_key=True)  # type: ignore[assignment]
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(  # type: ignore[assignment]
        "models.User", related_name="appointment_types", source_field="user"
    )
    user_id: str
    name: str = fields.CharField(max_length=255)  # type: ignore[assignment]
    duration_minutes: int = fields.IntField()  # type: ignore[assignment]

    class Meta:
        table = "appointment_types"


class Customer(Model):
    id: str = fields.CharField(max_length=128, primary_key=True)  # type: ignore[assignment]
    phone: str = fields.CharField(max_length=64, unique=True)  # type: ignore[assignment]
    name: str = fields.CharField(max_length=255)  # type: ignore[assignment]
    info: str | None = fields.TextField(null=True)  # type: ignore[assignment]

    class Meta:
        table = "customer"


class BlockedTime(Model):
    id: int = fields.IntField(primary_key=True)  # type: ignore[assignment]
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(  # type: ignore[assignment]
        "models.User", related_name="blocked_times", source_field="user"
    )
    user_id: str
    reason: str = fields.CharField(max_length=128)  # type: ignore[assignment]
    start: str = fields.CharField(max_length=64)  # type: ignore[assignment]
    end: str = fields.CharField(max_length=64)  # type: ignore[assignment]
    appointment_type: str | None = fields.CharField(max_length=255, null=True)  # type: ignore[assignment]
    customer: str | None = fields.CharField(max_length=128, null=True)  # type: ignore[assignment]
    google_event_id: str | None = fields.CharField(max_length=255, null=True)  # type: ignore[assignment]

    class Meta:
        table = "blocked_times"


class SchemaMigration(Model):
    id: int = fields.IntField(primary_key=True)  # type: ignore[assignment]
    name: str = fields.CharField(max_length=255, unique=True)  # type: ignore[assignment]

    class Meta:
        table = "schema_migrations"
