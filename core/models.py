from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.CharField(max_length=128, primary_key=True)
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=320, null=True)
    timezone = fields.CharField(
        max_length=128, default="America/Argentina/Buenos_Aires"
    )

    class Meta:
        table = "users"


class Rule(Model):
    id = fields.IntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="rules", source_field="user"
    )
    weekday = fields.IntField(null=True)
    start = fields.CharField(max_length=16)
    end = fields.CharField(max_length=16)
    rrule = fields.TextField(null=True)
    dtstart = fields.CharField(max_length=64, null=True)
    exclude_dates = fields.JSONField(null=True)

    class Meta:
        table = "rules"


class AppointmentType(Model):
    id = fields.IntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="appointment_types", source_field="user"
    )
    name = fields.CharField(max_length=255)
    duration_minutes = fields.IntField()

    class Meta:
        table = "appointment_types"


class Customer(Model):
    id = fields.CharField(max_length=128, primary_key=True)
    phone = fields.CharField(max_length=64, unique=True)
    name = fields.CharField(max_length=255)
    info = fields.TextField(null=True)

    class Meta:
        table = "customer"


class BlockedTime(Model):
    id = fields.IntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="blocked_times", source_field="user"
    )
    reason = fields.CharField(max_length=128)
    start = fields.CharField(max_length=64)
    end = fields.CharField(max_length=64)
    appointment_type = fields.CharField(max_length=255, null=True)
    customer = fields.CharField(max_length=128, null=True)
    google_event_id = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "blocked_times"


class SchemaMigration(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)

    class Meta:
        table = "schema_migrations"
