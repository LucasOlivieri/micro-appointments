from tortoise import fields
from tortoise.models import Model


class User(Model):
    id: str = fields.CharField(max_length=128, primary_key=True)
    name: str = fields.CharField(max_length=255)
    email: str | None = fields.CharField(max_length=320, null=True)
    message: str | None = fields.TextField(null=True)
    system_prompt: str | None = fields.TextField(null=True)
    timezone: str = fields.CharField(
        max_length=128, default="America/Argentina/Buenos_Aires"
    )

    class Meta:
        table = "users"


class Rule(Model):
    id: int = fields.IntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="rules", source_field="user"
    )
    user_id: str
    weekday: int | None = fields.IntField(null=True)
    start: str = fields.CharField(max_length=16)
    end: str = fields.CharField(max_length=16)
    rrule: str | None = fields.TextField(null=True)
    dtstart: str | None = fields.CharField(max_length=64, null=True)
    exclude_dates: list[str] | None = fields.JSONField(null=True)

    class Meta:
        table = "rules"


class AppointmentType(Model):
    id: int = fields.IntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="appointment_types", source_field="user"
    )
    user_id: str
    name: str = fields.CharField(max_length=255)
    duration_minutes: int = fields.IntField()
    advance_notice_minutes: int | None = fields.IntField(null=True)

    class Meta:
        table = "appointment_types"


class Customer(Model):
    id: str = fields.CharField(max_length=128, primary_key=True)
    phone: str = fields.CharField(max_length=64, unique=True)
    name: str = fields.CharField(max_length=255)
    info: str | None = fields.TextField(null=True)

    class Meta:
        table = "customer"


class BlockedTime(Model):
    id: int = fields.IntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="blocked_times", source_field="user"
    )
    user_id: str
    reason: str = fields.CharField(max_length=128)
    start: str = fields.CharField(max_length=64)
    end: str = fields.CharField(max_length=64)
    appointment_type: str | None = fields.CharField(max_length=255, null=True)
    customer: str | None = fields.CharField(max_length=128, null=True)
    google_event_id: str | None = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "blocked_times"


class SchemaMigration(Model):
    id: int = fields.IntField(primary_key=True)
    name: str = fields.CharField(max_length=255, unique=True)

    class Meta:
        table = "schema_migrations"
